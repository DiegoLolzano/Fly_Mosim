import time
from telemetry_receiver import MoSimTelemetryReceiver


def main():
  print("[Test Telemetría] Conectando receptor...")
  telemetry = MoSimTelemetryReceiver(ip="127.0.0.1", port=9999)
  telemetry.start()

  print(
      "Esperando datos de MoSimulator (asegúrate de que el juego esté"
      " corriendo)..."
  )
  try:
    while True:
      pose = telemetry.get_pose()
      corals = telemetry.get_corals()
      closest = telemetry.get_closest_coral()

      if pose.name:
        status_coral = "SI" if pose.has_coral else "NO"
        print(
            f"Robot: {pose.name} | Pos: ({pose.x:.2f}, {pose.z:.2f}) | Yaw:"
            f" {pose.yaw:5.1f}° | Corales en piso: {len(corals)} | ¿Tiene"
            f" Coral?: [{status_coral}]",
            end="\r",
        )

        if corals and closest:
          pass

      time.sleep(0.1)

  except KeyboardInterrupt:
    print("\nPrueba finalizada.")
  finally:
    telemetry.stop()


if __name__ == "__main__":
  main()