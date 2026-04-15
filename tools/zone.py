import cv2
import numpy as np
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk


class ZoneSelector:
    def __init__(self, video_path):
        self.points = []

        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise RuntimeError(f"Error loading video: {video_path}")

        self.frame = cv2.resize(frame, (900, 600))
        image_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        self.image = Image.fromarray(image_rgb)

        self.root = tk.Tk()
        self.root.title("Homography Zone Selector")

        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas = tk.Canvas(
            self.root,
            width=self.tk_image.width(),
            height=self.tk_image.height(),
        )
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("r", self.reset)

        self.label = tk.Label(
            self.root,
            text="Click in order: TL -> TR -> BR -> BL\nPress R to reset",
            font=("Arial", 12),
        )
        self.label.pack()

        self.root.mainloop()

    def draw(self):
        self.canvas.delete("overlay")

        for i, (x, y) in enumerate(self.points):
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="red", tags="overlay")
            self.canvas.create_text(
                x + 10,
                y - 10,
                text=str(i + 1),
                fill="yellow",
                font=("Arial", 14, "bold"),
                tags="overlay",
            )

        if len(self.points) > 1:
            for i in range(len(self.points) - 1):
                self.canvas.create_line(
                    *self.points[i],
                    *self.points[i + 1],
                    fill="blue",
                    width=2,
                    tags="overlay",
                )

        if len(self.points) == 4:
            self.canvas.create_line(
                *self.points[3],
                *self.points[0],
                fill="green",
                width=3,
                tags="overlay",
            )

    def on_click(self, event):
        if len(self.points) >= 4:
            return

        x, y = event.x, event.y
        self.points.append((x, y))
        print(f"Point {len(self.points)}: ({x}, {y})")
        self.draw()

        if len(self.points) == 4:
            print(f"\nFinal points: {self.points}")
            self.process_homography()

    def reset(self, event=None):
        self.points = []
        self.canvas.delete("overlay")
        print("\nReset points")

    @staticmethod
    def order_points(pts):
        pts = np.array(pts, dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        return np.array(
            [
                pts[np.argmin(s)],
                pts[np.argmin(diff)],
                pts[np.argmax(s)],
                pts[np.argmax(diff)],
            ],
            dtype="float32",
        )

    @staticmethod
    def get_dst_size(pts):
        (tl, tr, br, bl) = pts
        width_a = np.linalg.norm(br - bl)
        width_b = np.linalg.norm(tr - tl)
        max_width = int(max(width_a, width_b))

        height_a = np.linalg.norm(tr - br)
        height_b = np.linalg.norm(tl - bl)
        max_height = int(max(height_a, height_b))
        return max_width, max_height

    def process_homography(self):
        src = self.order_points(self.points)
        w, h = self.get_dst_size(src)

        dst = np.array(
            [
                [0, 0],
                [w - 1, 0],
                [w - 1, h - 1],
                [0, h - 1],
            ],
            dtype=np.float32,
        )

        h_mat = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(self.frame, h_mat, (w, h))

        cv2.imshow("Warped Output", warped)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parents[2]
    video = root_dir / "Speed_Detection_Pipeline" / "data" / "testing_1.mp4"
    ZoneSelector(str(video))
