import enum
import math
import time
from field_map import WAYPOINTS, get_waypoint
from telemetry_receiver import MoSimTelemetryReceiver
import vgamepad as vg


class PIDController:

  def __init__(
      self,
      kp: float,
      ki: float = 0.0,
      kd: float = 0.0,
      max_integral: float = 0.5,
  ):
    self.kp = kp
    self.ki = ki
    self.kd = kd
    self.max_integral = max_integral
    self.prev_error = 0.0
    self.integral = 0.0

  def calculate(self, error: float, dt: float = 0.02) -> float:
    self.integral += error * dt
    self.integral = max(
        min(self.integral, self.max_integral), -self.max_integral
    )
    derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
    self.prev_error = error
    return (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)

  def reset(self):
    self.prev_error = 0.0
    self.integral = 0.0


def normalize_angle(angle_deg: float) -> float:
  while angle_deg > 180.0:
    angle_deg -= 360.0
  while angle_deg < -180.0:
    angle_deg += 360.0
  return angle_deg


def clamp(val: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
  return max(min(val, max_val), min_val)


class RobotState(enum.Enum):
  NAV_TO_FEEDER = 1
  HUNTING_CORAL = 2
  NAV_TO_REEF = 3
  SCORING = 4


class AutonomousBrain:

  def __init__(self):
    print("[La Mosca Brain] Inicializando Gamepad virtual...")
    self.gamepad = vg.VX360Gamepad()
    time.sleep(1.0)

    print("[La Mosca Brain] Conectando receptor de telemetría...")
    self.telemetry = MoSimTelemetryReceiver(ip="127.0.0.1", port=9999)
    self.telemetry.start()

    self.pid_x = PIDController(kp=0.85, kd=0.07)
    self.pid_z = PIDController(kp=0.85, kd=0.07)
    self.pid_yaw = PIDController(kp=0.035, ki=0.001, kd=0.004)
    self.pid_hunt_yaw = PIDController(kp=0.035, kd=0.004)
    self.pid_hunt_fwd = PIDController(kp=0.75, kd=0.05)

    self.state = RobotState.NAV_TO_FEEDER
    self.current_target_face = "reef_1"
    self.face_rotation = ["reef_1", "reef_6", "reef_2", "reef_5"]
    self.face_idx = 0
    self.score_count = 0

  def stow(self):
    self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
    self.gamepad.update()
    time.sleep(0.18)
    self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
    self.gamepad.update()
    time.sleep(0.12)

  def set_elevator(self, level: str):
    buttons = {
        "L1": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
        "L2": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
        "L3": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
        "L4": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    }
    if level in buttons:
      btn = buttons[level]
      self.gamepad.press_button(button=btn)
      self.gamepad.update()
      time.sleep(0.18)
      self.gamepad.release_button(button=btn)
      self.gamepad.update()
    elif level == "STOW":
      self.stow()

  def stop_driving(self):
    self.gamepad.left_joystick_float(0.0, 0.0)
    self.gamepad.right_joystick_float(0.0, 0.0)
    self.gamepad.update()

  def drive_towards(self, target: dict, pose, tol_dist=0.22, tol_yaw=6.0):
    err_x = target["x"] - pose.x
    err_z = target["z"] - pose.z
    dist = math.hypot(err_x, err_z)
    err_yaw = normalize_angle(target["yaw"] - pose.yaw)

    if dist < tol_dist and abs(err_yaw) < tol_yaw:
      self.stop_driving()
      return True

    yaw_rad = math.radians(pose.yaw)
    local_forward = err_z * math.cos(yaw_rad) + err_x * math.sin(yaw_rad)
    local_strafe = err_x * math.cos(yaw_rad) - err_z * math.sin(yaw_rad)

    cmd_forward = clamp(self.pid_z.calculate(local_forward))
    cmd_strafe = clamp(self.pid_x.calculate(local_strafe))

    raw_turn = self.pid_yaw.calculate(err_yaw)
    min_turn = 0.11
    if abs(err_yaw) > tol_yaw:
      cmd_turn = clamp(
          max(raw_turn, min_turn) if raw_turn > 0 else min(raw_turn, -min_turn)
      )
    else:
      cmd_turn = 0.0

    self.gamepad.left_joystick_float(
        x_value_float=cmd_strafe, y_value_float=cmd_forward
    )
    self.gamepad.right_joystick_float(x_value_float=cmd_turn, y_value_float=0.0)
    self.gamepad.update()
    return False

  def select_next_reef_face(self, pose):
    """Alterna entre las caras frontales del Reef más accesibles."""
    face = self.face_rotation[self.face_idx % len(self.face_rotation)]
    self.face_idx += 1
    return face

  def run_match_loop(self):
    print("Esperando telemetría del robot...")
    while True:
      pose = self.telemetry.get_pose()
      if pose.name:
        print(f"-> Conectado a: {pose.name} | Estado Inicial: {self.state.name}")
        break
      time.sleep(0.05)

    feeder_wp = get_waypoint("human_der")
    hunt_timeout_start = 0.0
    hunt_started = False

    try:
      while True:
        pose = self.telemetry.get_pose()

        # ==========================================
        # 1. ESTADO: VIAJAR A ESTACIÓN HUMANA
        # ==========================================
        if self.state == RobotState.NAV_TO_FEEDER:
          # Si por alguna razón ya tiene coral, abortar viaje e ir al Reef
          if pose.has_coral:
            self.current_target_face = self.select_next_reef_face(pose)
            self.state = RobotState.NAV_TO_REEF
            continue

          reached = self.drive_towards(feeder_wp, pose, tol_dist=0.35)
          # Si llegó o ya detecta corales en la rampa, pasar a cazar
          coral_cercano = self.telemetry.get_closest_coral_near(
              (feeder_wp["x"], feeder_wp["z"]), max_dist=3.0
          )
          if reached or coral_cercano:
            self.stop_driving()
            self.state = RobotState.HUNTING_CORAL
            hunt_started = False
            self.pid_hunt_fwd.reset()
            self.pid_hunt_yaw.reset()

        # ==========================================
        # 2. ESTADO: CAZA REACTIVA DE CORAL
        # ==========================================
        elif self.state == RobotState.HUNTING_CORAL:
          if not hunt_started:
            print("\n[Caza] Desplegando intake y activando rodillos...")
            self.set_elevator("L1")
            self.gamepad.left_trigger_float(1.0)
            self.gamepad.update()
            hunt_timeout_start = time.time()
            hunt_started = True

          # Condición de éxito: Pieza asegurada dentro del robot
          if pose.has_coral:
            print("\n[Caza] ¡Coral asegurado adentro! Cancelando rodillos.")
            self.gamepad.left_trigger_float(0.0)
            self.stop_driving()
            self.stow()

            self.current_target_face = self.select_next_reef_face(pose)
            print(f"[Cerebro] Ruteando hacia {self.current_target_face}...")
            self.pid_x.reset()
            self.pid_z.reset()
            self.pid_yaw.reset()
            self.state = RobotState.NAV_TO_REEF
            continue

          # Timeout de búsqueda si no cae nada
          if time.time() - hunt_timeout_start > 7.0:
            print("\n[Caza] Tiempo de espera agotado. Reintentando...")
            self.gamepad.left_trigger_float(0.0)
            self.stow()
            self.state = RobotState.NAV_TO_FEEDER
            continue

          target_coral = self.telemetry.get_closest_coral_near(
              (feeder_wp["x"], feeder_wp["z"]), max_dist=4.0
          )
          if target_coral is None:
            # Espera activa avanzando suave
            self.gamepad.left_joystick_float(0.0, 0.12)
            self.gamepad.right_joystick_float(0.0, 0.0)
            self.gamepad.update()
            time.sleep(0.03)
            continue

          cx, cz = target_coral
          dx = cx - pose.x
          dz = cz - pose.z
          dist = math.hypot(dx, dz)

          desired_yaw = math.degrees(math.atan2(dx, dz))
          err_yaw = normalize_angle(desired_yaw - pose.yaw)

          cmd_turn = clamp(self.pid_hunt_yaw.calculate(err_yaw), -0.65, 0.65)
          cmd_fwd = clamp(self.pid_hunt_fwd.calculate(dist), 0.18, 0.45)
          if abs(err_yaw) > 20.0:
            cmd_fwd *= 0.35

          self.gamepad.left_joystick_float(
              x_value_float=0.0, y_value_float=cmd_fwd
          )
          self.gamepad.right_joystick_float(
              x_value_float=cmd_turn, y_value_float=0.0
          )
          self.gamepad.update()

        # ==========================================
        # 3. ESTADO: NAVEGACIÓN HACIA EL REEF
        # ==========================================
        elif self.state == RobotState.NAV_TO_REEF:
          target_wp = get_waypoint(self.current_target_face)
          reached = self.drive_towards(target_wp, pose, tol_dist=0.22)

          if reached:
            self.stop_driving()
            self.state = RobotState.SCORING

        # ==========================================
        # 4. ESTADO: ANOTACIÓN (SCORE)
        # ==========================================
        elif self.state == RobotState.SCORING:
          print(f"\n[Score] Anotando en {self.current_target_face}...")

          # Alineación asistida con bumper
          self.gamepad.press_button(
              button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER
          )
          for _ in range(6):
            self.gamepad.left_joystick_float(0.0, 0.28)
            self.gamepad.update()
            time.sleep(0.1)
          self.stop_driving()
          self.gamepad.release_button(
              button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER
          )
          self.gamepad.update()

          # Elevación y disparo
          self.set_elevator("L4")
          time.sleep(0.85)

          for _ in range(4):
            self.gamepad.right_trigger_float(1.0)
            self.gamepad.update()
            time.sleep(0.1)
          self.gamepad.right_trigger_float(0.0)
          self.gamepad.update()
          time.sleep(0.2)

          self.stow()
          self.score_count += 1
          print(f"-> [Score Completado] Total piezas anotadas: {self.score_count}")

          # Transición inmediata al alimentador
          self.pid_x.reset()
          self.pid_z.reset()
          self.pid_yaw.reset()
          self.state = RobotState.NAV_TO_FEEDER

        time.sleep(0.02)

    except KeyboardInterrupt:
      print("\n[La Mosca Brain] Partida detenida por el usuario.")
    finally:
      self.stop_driving()
      self.gamepad.left_trigger_float(0.0)
      self.gamepad.right_trigger_float(0.0)
      self.gamepad.update()
      self.telemetry.stop()


if __name__ == "__main__":
  brain = AutonomousBrain()
  brain.run_match_loop()