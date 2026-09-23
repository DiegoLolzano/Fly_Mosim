import keyboard
import pickle

def grabar_rutina(nombre_archivo):
    print(f"\nPreparando para grabar: {nombre_archivo}")
    print("Ve a MoSimulator. Empieza a conducir y presiona 'END' cuando termines la ruta.")
    
    # Cambiamos la tecla de corte aquí
    eventos = keyboard.record(until='end')
    
    with open(f'{nombre_archivo}.pkl', 'wb') as f:
        pickle.dump(eventos, f)
    print(f"¡Ruta {nombre_archivo} guardada con éxito!")

# Graba tus rutinas
grabar_rutina('ruta_roja_constante')
grabar_rutina('ruta_azul_1')
grabar_rutina('ruta_azul_2')
grabar_rutina('ruta_verde_1')