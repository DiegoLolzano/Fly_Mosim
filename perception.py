# perception.py
import cv2
import numpy as np

LOWER_CORAL = np.array([0, 0, 195])
UPPER_CORAL = np.array([180, 40, 255])

LOWER_REEF = np.array([130, 70, 60])
UPPER_REEF = np.array([170, 255, 255])

class GamePerception:
    def __init__(self, width=640, height=480):
        self.w = width
        self.h = height

    def extract_features(self, frame_bgr):
        clean_frame = frame_bgr.copy()

        # 1. Enmascarar HUD inferior (marcador)
        clean_frame[self.h - 65:self.h, :] = 0

        hsv = cv2.cvtColor(clean_frame, cv2.COLOR_BGR2HSV)

        # 2. Localizar robot (bumpers azules) con umbral más sensible
        lower_blue = np.array([95, 100, 40])
        upper_blue = np.array([135, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        robot_pos = self._get_center(blue_mask, min_area=70)

        # Si por ángulo de cámara no detecta el azul, estimar su posición central inferior fija
        if robot_pos is None:
            robot_pos = (int(self.w * 0.5), int(self.h * 0.78))

        # 3. Detectar Reef
        reef_mask = cv2.inRange(hsv, LOWER_REEF, UPPER_REEF)
        reef_pos, reef_area = self._get_reef_target(reef_mask)

        # 4. Detectar Coral
        coral_mask = cv2.inRange(hsv, LOWER_CORAL, UPPER_CORAL)
        # Ignorar tercio superior (gradas)
        coral_mask[:int(self.h * 0.35), :] = 0
        # Ignorar la zona inmediata del intake propio para no autotargetearse
        coral_mask[int(self.h * 0.70):, int(self.w * 0.35):int(self.w * 0.65)] = 0
        
        coral_pos = self._get_field_coral(coral_mask, robot_pos)

        # Dibujar marcas visuales
        if robot_pos:
            cv2.circle(clean_frame, robot_pos, 7, (255, 120, 0), -1)
        if coral_pos:
            cv2.circle(clean_frame, coral_pos, 7, (0, 255, 0), -1)
        if reef_pos:
            cv2.circle(clean_frame, reef_pos, 9, (255, 0, 255), -1)

        return {
            "robot": robot_pos,
            "coral": coral_pos,
            "reef": reef_pos,
            "reef_area": reef_area
        }, clean_frame

    def _get_center(self, mask, min_area):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < min_area:
            return None
        M = cv2.moments(c)
        if M["m00"] == 0:
            return None
        return int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])

    def _get_reef_target(self, mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, 0
        c = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(c)
        if area < 50:
            return None, 0
        
        # En vez de apuntar a la copa de las ramas, apuntar a la base inferior del contorno
        x, y, w, h = cv2.boundingRect(c)
        base_x = x + (w // 2)
        base_y = y + h - 10  # Punto bajo del arrecife

        return (base_x, base_y), area

    def _get_field_coral(self, mask, robot_pos):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        best_pos = None
        min_dist = 9999.0

        for c in contours:
            area = cv2.contourArea(c)
            if 25 < area < 4000:
                _, _, w_box, _ = cv2.boundingRect(c)
                if w_box < (self.w * 0.28):
                    M = cv2.moments(c)
                    if M["m00"] == 0:
                        continue
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    rx, ry = robot_pos
                    d = np.hypot(cx - rx, cy - ry)
                    if d < 55:  # Muy cerca del centro del robot
                        continue

                    if d < min_dist:
                        min_dist = d
                        best_pos = (cx, cy)

        return best_pos