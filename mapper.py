import time
from telemetry_receiver import MoSimTelemetryReceiver

def main():
    telemetry = MoSimTelemetryReceiver(ip="127.0.0.1", port=9999)
    telemetry.start()
    
    print("=" * 55)
    print(" MODO MAPEO MANUAL: Conduce el robot con tu control")
    print(" Presiona ENTER para capturar un Waypoint.")
    print(" Escribe 'exit' y ENTER para terminar.")
    print("=" * 55)

    try:
        while True:
            pose = telemetry.get_pose()
            if pose.name:
                break
            time.sleep(0.05)

        puntos_guardados = []

        while True:
            pose = telemetry.get_pose()
            nombre_wp = input(f"\n[Pose actual: X={pose.x:6.2f}, Z={pose.z:6.2f}, Yaw={pose.yaw:5.1f}°] Nombre del punto: ")
            
            if nombre_wp.strip().lower() == "exit":
                break
            
            if not nombre_wp.strip():
                nombre_wp = f"Punto_{len(puntos_guardados) + 1}"

            # Capturar la pose exacta del momento
            pose = telemetry.get_pose()
            wp_dict = {
                "name": nombre_wp,
                "x": round(pose.x, 2),
                "z": round(pose.z, 2),
                "yaw": round(pose.yaw, 1)
            }
            puntos_guardados.append(wp_dict)
            print(f" -> Guardado: {wp_dict}")

        print("\n--- LISTA LISTA PARA COPIAR A LA MOSCA ---")
        print("WAYPOINTS = [")
        for p in puntos_guardados:
            print(f'    {{"name": "{p["name"]}", "x": {p["x"]}, "z": {p["z"]}, "yaw": {p["yaw"]}}},')
        print("]")

    except KeyboardInterrupt:
        pass
    finally:
        telemetry.stop()

if __name__ == "__main__":
    main()