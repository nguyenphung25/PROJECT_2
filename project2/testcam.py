import cv2

for index in range(5):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print(f"Camera {index}: KHONG MO DUOC")
        continue

    ret, frame = cap.read()

    if ret:
        print(f"Camera {index}: MO DUOC")

        cv2.imshow(f"Camera {index}", frame)
        print("Nhan phim bat ky de xem camera tiep theo...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print(f"Camera {index}: MO DUOC NHUNG KHONG DOC DUOC FRAME")

    cap.release()