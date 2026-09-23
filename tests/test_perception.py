# test_perception.py
import mss
import cv2
import numpy as np
from perception import GamePerception

# Coordenadas de tu ventana de MoSim
CAPTURE_REGION = {'top': 40, 'left': 10, 'width': 640, 'height': 480}

sct = mss.mss()
detector = GamePerception(width=640, height=480)

print("Probando percepción limpia. Presiona 'q' para salir.")

while True:
    scr_img = np.array(sct.grab(CAPTURE_REGION))
    frame = cv2.cvtColor(scr_img, cv2.COLOR_BGRA2BGR)

    obs, processed_view = detector.extract_features(frame)
    
    # Imprimir el vector sensorial que irá al cerebro
    print(f"\rCoral: [Ang: {obs[0]:+.2f}, Prox: {obs[1]:.2f}] | Reef: [Ang: {obs[2]:+.2f}, Prox: {obs[3]:.2f}]", end="")

    cv2.imshow("Mascara Limpia", processed_view)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()