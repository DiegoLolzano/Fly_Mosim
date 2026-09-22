import os
from mosim_env import MoSimHuntEnv
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback

def main():
    # Crear carpetas para guardar la "memoria" del robot
    models_dir = "models/PPO_Mosca"
    logs_dir = "logs"
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    print("[IA] Inicializando Entorno y Red Neuronal PPO...")
    env = MoSimHuntEnv()

    # Configuración de la red neuronal
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=0.0003,
        n_steps=1024,
        batch_size=64,
        gamma=0.99,
        verbose=1,
        tensorboard_log=logs_dir
    )

    # Autoguardado: Guardará un modelo nuevo cada 5,000 pasos automáticamente
    checkpoint_callback = CheckpointCallback(
        save_freq=5000,
        save_path=models_dir,
        name_prefix="mosca_cazador_cp"
    )

    print("[IA] ¡Iniciando entrenamiento! Ve a MoSimulator y suelta unos corales cerca del robot.")
    
    try:
        # Entrenar por 30,000 pasos con el autoguardado activado
        model.learn(total_timesteps=30000, callback=checkpoint_callback, progress_bar=True)
        
        # Guardado final si llega al 100% de forma natural
        model.save(f"{models_dir}/mosca_cazador_final")
        print("\n[IA] Entrenamiento finalizado y modelo guardado.")
    except KeyboardInterrupt:
        print("\n[IA] Entrenamiento interrumpido por el usuario (Ctrl+C). Guardando progreso...")
        model.save(f"{models_dir}/mosca_cazador_interrumpido")
    finally:
        env.close()

if __name__ == "__main__":
    main()