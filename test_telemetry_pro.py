import time
from telemetry_receiver import MoSimTelemetryReceiver

def main():
    print("[Diagnóstico Pro] Escuchando telemetría avanzada...")
    telemetry = MoSimTelemetryReceiver(ip="127.0.0.1", port=9999)
    telemetry.start()

    try:
        while True:
            pose = telemetry.get_pose()
            if pose.name:
                # Traducción de estados
                piece_str = "Vacio"
                if pose.piece_type == 1: piece_str = "CORAL"
                elif pose.piece_type == 2: piece_str = "ALGAE"
                
                index_str = "NO"
                if pose.piece_type != 0:
                    index_str = "STOW/End-Effector" if pose.is_indexed == 1 else "Hopper (Abajo)"

                algae = telemetry.get_algae()
                corals = telemetry.get_corals()
                
                # Contar algas en el Reef (Altura Y > 0.5)
                algas_en_reef = sum(1 for a in algae if a.y > 0.5)
                
                print(f"Robot: {pose.name[:6]} | Pieza: {piece_str} | Indexado: {index_str} | Algas en Reef: {algas_en_reef} | Corales suelo: {len(corals)}", end="\r")
            
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nDiagnóstico finalizado.")
    finally:
        telemetry.stop()

if __name__ == "__main__":
    main()