import time
import math
from telemetry_receiver import MoSimTelemetryReceiver

def main():
    print("[Debug] Iniciando conexión con MoSimulator...")
    telemetry = MoSimTelemetryReceiver(ip="127.0.0.1", port=9999)
    telemetry.start()
    time.sleep(1.0) # Dar tiempo a que lleguen los primeros paquetes

    print("\n[Debug] Leyendo telemetría. Conduce manualmente y apunta el INTAKE al coral.")
    print("Presiona Ctrl+C para salir.\n")
    
    try:
        while True:
            pose = telemetry.get_pose()
            closest_coral = telemetry.get_closest_piece(piece_type="CORAL")
            
            if closest_coral:
                cx, _, cz = closest_coral
                dx = cx - pose.x
                dz = cz - pose.z
                
                # Ángulo actual del robot
                yaw_rad = math.radians(pose.yaw)
                
                # 1. Cálculo Original (dx, dz)
                target_orig_rad = math.atan2(dx, dz)
                err_orig_rad = (target_orig_rad - yaw_rad + math.pi) % (2 * math.pi) - math.pi
                
                # 2. Cálculo Invertido (-dx, -dz)
                target_inv_rad = math.atan2(-dx, -dz)
                err_inv_rad = (target_inv_rad - yaw_rad + math.pi) % (2 * math.pi) - math.pi
                
                print(f"---")
                print(f"Yaw del Chasis: {pose.yaw:.1f}°")
                print(f"Error Original : {math.degrees(err_orig_rad):+7.1f}° (0° = alineado)")
                print(f"Error Invertido: {math.degrees(err_inv_rad):+7.1f}° (0° = alineado)")
            else:
                print("Esperando detectar un coral en la cancha...")
            
            time.sleep(0.5) # Actualizar 2 veces por segundo para poder leerlo
            
    except KeyboardInterrupt:
        print("\n[Debug] Diagnóstico terminado.")
    finally:
        telemetry.stop()

if __name__ == "__main__":
    main()