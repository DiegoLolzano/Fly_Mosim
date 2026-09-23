import time
from stable_baselines3 import PPO
from mosim_env import MoSimHuntEnv

def main():
    print("\n[Demo] Iniciando evaluación del agente...")
    
    # 1. Inicializar el entorno
    env = MoSimHuntEnv()
    
    # 2. Cargar el modelo entrenado
    # IMPORTANTE: Cambia este string por el nombre exacto de tu archivo .zip dentro de models/
    # (por ejemplo: "models/mosca_cazador_cp_30000_steps")
    model_path = "models/PPO_Mosca/mosca_cazador_final"
    
    try:
        model = PPO.load(model_path, env=env)
        print(f"[Demo] Modelo cargado exitosamente desde: {model_path}.zip")
    except Exception as e:
        print(f"\n[Error] No se encontró el modelo. Verifica el nombre en tu carpeta models/. Detalle: {e}")
        return

    # 3. Bucle de ejecución (Inferencia)
    obs, _ = env.reset()
    print("[Demo] ¡Arrancando! Observa a La Mosca en acción.")
    
    try:
        while True:
            # deterministic=True obliga a la IA a tomar la mejor decisión calculada, sin experimentar al azar
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            
            # Si el robot atrapa el coral (terminated) o presionas 'R' (truncated), se reinicia
            if terminated or truncated:
                print("[Demo] Ciclo completado. Esperando reinicio...")
                # Aquí el entorno hace su propia pausa de 'R' y 20 segundos gracias a tu función reset()
                obs, _ = env.reset()
                
    except KeyboardInterrupt:
        print("\n[Demo] Evaluación detenida manualmente.")
    finally:
        env.close()

if __name__ == "__main__":
    main()