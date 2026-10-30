import os
import sys
import math
import queue
import shutil
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "Studio Musik Otomatis"

def find_tool(name):
    found = shutil.which(name)
    if found:
        return found
    # Also check a local ffmpeg/bin folder beside this script
    local = Path(__file__).resolve().parent / "ffmpeg" / "bin" / (name + (".exe" if os.name == "nt" else ""))
    return str(local) if local.exists() else None

def run_capture(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")

def probe_duration(ffprobe, file_path):
    result = run_capture([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
    ])
    if result.returncode != 0:
        raise RuntimeError(f"Gagal membaca durasi:\n{file_path}\n{result.stderr[-1000:]}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(f"Durasi file tidak terbaca: {file_path}")

def ff_escape(value):
    # Escape text for FFmpeg filter syntax.
    return (str(value).replace("\\", r"\\")
            .replace(":", r"\:")
            .replace("'", r"\'")
            .replace(",", r"\,")
            .replace("[", r"\[")
            .replace("]", r"\]")
            .replace("%", r"\%")
            .replace("\n", " "))

def timecode(seconds):
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

class MusicVideoStudio:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1050x760")
        self.root.minsize(900, 650)
        self.root.configure(bg="#111827")
        self.tracks = []
        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.home() / "Videos"))
        self.ratio = tk.StringVar(value="16:9")
        self.quality = tk.StringVar(value="1080p")
        self.crossfade = tk.StringVar(value="3")
        self.show_titles = tk.BooleanVar(value=True)
        self.make_timestamps = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Siap. Tambahkan lagu dan video latar.")
        self.events = queue.Queue()
        self.rendering = False
        self._style()
        self._build()
        self.root.after(150, self._poll_events)

    def _style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#111827")
        style.configure("Panel.TFrame", background="#1f2937")
        style.configure("TLabel", background="#111827", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background="#1f2937", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#111827", foreground="#ffffff", font=("Segoe UI", 21, "bold"))
        style.configure("Sub.TLabel", background="#111827", foreground="#9ca3af", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", background="#7c3aed", foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#6d28d9")])
        style.configure("Treeview", background="#111827", foreground="#e5e7eb", fieldbackground="#111827", rowheight=29)
        style.configure("Treeview.Heading", background="#374151", foreground="white", font=("Segoe UI", 9, "bold"))
        style.configure("TCheckbutton", background="#1f2937", foreground="#e5e7eb")
        style.configure("TRadiobutton", background="#1f2937", foreground="#e5e7eb")

    def _build(self):
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="♫  STUDIO MUSIK OTOMATIS", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header, text="Buat video musik panjang secara otomatis langsung dari komputer Anda.", style="Sub.TLabel").pack(anchor="w", pady=(3, 0))

        top = ttk.Frame(outer)
        top.pack(fill="x", pady=(0, 12))
        self._panel(top, "1. VIDEO LATAR")
        video_panel = top.winfo_children()[-1]
        ttk.Entry(video_panel, textvariable=self.video_path).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(video_panel, text="Pilih Video Latar", command=self.pick_video).pack(side="left")

        mid = ttk.Frame(outer)
        mid.pack(fill="both", expand=True)
        left = ttk.Frame(mid, style="Panel.TFrame", padding=12)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = ttk.Frame(mid, style="Panel.TFrame", padding=12, width=300)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        ttk.Label(left, text="2. DAFTAR PUTAR MUSIK", style="Panel.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(left, text="Tambahkan banyak lagu sekaligus. Urutannya dapat diubah.", style="Panel.TLabel").pack(anchor="w", pady=(3, 9))
        columns = ("number", "title", "duration")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("number", text="#")
        self.tree.heading("title", text="Judul Lagu")
        self.tree.heading("duration", text="Lama")
        self.tree.column("number", width=42, anchor="center")
        self.tree.column("title", width=440)
        self.tree.column("duration", width=85, anchor="center")
        self.tree.pack(fill="both", expand=True)
        btns = ttk.Frame(left, style="Panel.TFrame")
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="+ Tambah Lagu", command=self.add_tracks).pack(side="left")
        ttk.Button(btns, text="Hapus Lagu", command=self.remove_tracks).pack(side="left", padx=5)
        ttk.Button(btns, text="↑ Pindah Naik", command=lambda: self.move_track(-1)).pack(side="left", padx=5)
        ttk.Button(btns, text="↓ Pindah Turun", command=lambda: self.move_track(1)).pack(side="left")

        ttk.Label(right, text="3. PENGATURAN VIDEO", style="Panel.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        self._setting_label(right, "Ukuran Video")
        ratio_box = ttk.Frame(right, style="Panel.TFrame")
        ratio_box.pack(fill="x", pady=(2, 8))
        ttk.Radiobutton(ratio_box, text="Mendatar 16:9 (YouTube)", variable=self.ratio, value="16:9").pack(anchor="w")
        ttk.Radiobutton(ratio_box, text="Tegak 9:16 (Shorts)", variable=self.ratio, value="9:16").pack(anchor="w")
        self._setting_label(right, "Kualitas Video")
        ttk.Combobox(right, textvariable=self.quality, values=["1080p", "2K", "4K"], state="readonly").pack(fill="x", pady=(2, 8))
        self._setting_label(right, "Durasi perpindahan lagu (detik)")
        ttk.Combobox(right, textvariable=self.crossfade, values=["0", "1", "2", "3", "5", "8"], state="readonly").pack(fill="x", pady=(2, 8))
        ttk.Checkbutton(right, text="Tampilkan judul lagu", variable=self.show_titles).pack(anchor="w", pady=3)
        ttk.Checkbutton(right, text="Buat penanda waktu YouTube", variable=self.make_timestamps).pack(anchor="w", pady=3)
        ttk.Separator(right).pack(fill="x", pady=12)
        self._setting_label(right, "Folder penyimpanan hasil")
        outrow = ttk.Frame(right, style="Panel.TFrame")
        outrow.pack(fill="x", pady=(2, 8))
        ttk.Entry(outrow, textvariable=self.output_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(outrow, text="…", width=3, command=self.pick_output).pack(side="left", padx=(5, 0))
        ttk.Button(right, text="▶  MULAI RENDER", style="Accent.TButton", command=self.start_render).pack(fill="x", pady=(12, 5))
        ttk.Label(right, text="Pembuatan video dilakukan di komputer. Waktu proses bergantung pada durasi dan kemampuan komputer.", style="Panel.TLabel", wraplength=260).pack(anchor="w", pady=(5, 0))

        bottom = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        bottom.pack(fill="x", pady=(12, 0))
        self.progress = ttk.Progressbar(bottom, mode="indeterminate")
        self.progress.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status, style="Panel.TLabel").pack(anchor="w", pady=(7, 0))

    def _panel(self, parent, title):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        panel.pack(fill="x")
        ttk.Label(panel, text=title, style="Panel.TLabel", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 12))
        return panel

    def _setting_label(self, parent, text):
        ttk.Label(parent, text=text, style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5, 0))

    def pick_video(self):
        path = filedialog.askopenfilename(title="Pilih video latar", filetypes=[("Berkas video", "*.mp4 *.mov *.mkv *.avi *.webm"), ("Semua berkas", "*.*")])
        if path:
            self.video_path.set(path)

    def pick_output(self):
        path = filedialog.askdirectory(title="Pilih folder penyimpanan video")
        if path:
            self.output_dir.set(path)

    def add_tracks(self):
        paths = filedialog.askopenfilenames(title="Pilih berkas musik", filetypes=[("Berkas audio", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"), ("Semua berkas", "*.*")])
        for p in paths:
            if p not in self.tracks:
                self.tracks.append(p)
        self.refresh_list()

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, path in enumerate(self.tracks, 1):
            self.tree.insert("", "end", iid=str(i-1), values=(i, Path(path).stem, "—"))

    def remove_tracks(self):
        indexes = sorted((int(x) for x in self.tree.selection()), reverse=True)
        for i in indexes:
            if 0 <= i < len(self.tracks):
                self.tracks.pop(i)
        self.refresh_list()

    def move_track(self, direction):
        selected = self.tree.selection()
        if len(selected) != 1:
            return
        i = int(selected[0])
        j = i + direction
        if 0 <= j < len(self.tracks):
            self.tracks[i], self.tracks[j] = self.tracks[j], self.tracks[i]
            self.refresh_list()
            self.tree.selection_set(str(j))

    def start_render(self):
        if self.rendering:
            return
        if not self.tracks:
            messagebox.showwarning("Daftar putar masih kosong", "Tambahkan minimal satu lagu terlebih dahulu.")
            return
        if not self.video_path.get() or not Path(self.video_path.get()).is_file():
            messagebox.showwarning("Video latar belum dipilih", "Pilih video latar terlebih dahulu.")
            return
        if not Path(self.output_dir.get()).is_dir():
            messagebox.showwarning("Folder penyimpanan tidak valid", "Pilih folder penyimpanan yang tersedia.")
            return
        ffmpeg = find_tool("ffmpeg")
        ffprobe = find_tool("ffprobe")
        if not ffmpeg or not ffprobe:
            messagebox.showerror("Mesin pengolah video belum ditemukan", "FFmpeg belum terpasang atau belum dikenali Windows.\nBaca file PETUNJUK.txt untuk petunjuk pemasangan.")
            return
        self.rendering = True
        self.progress.start(12)
        self.status.set("Menyiapkan daftar putar dan menghitung lama lagu…")
        thread = threading.Thread(target=self._render_worker, args=(ffmpeg, ffprobe), daemon=True)
        thread.start()

    def _render_worker(self, ffmpeg, ffprobe):
        try:
            durations = [probe_duration(ffprobe, p) for p in self.tracks]
            crossfade = max(0.0, float(self.crossfade.get()))
            if len(durations) > 1:
                crossfade = min(crossfade, max(0.0, min(durations) - 0.1))
            else:
                crossfade = 0.0

            starts = []
            cursor = 0.0
            for d in durations:
                starts.append(cursor)
                cursor += d - crossfade
            total = cursor + (crossfade if len(durations) > 1 else 0)
            # Correct total: N tracks with N-1 crossfades.
            total = sum(durations) - crossfade * (len(durations) - 1)

            ratio = self.ratio.get()
            res = self.quality.get()
            if ratio == "16:9":
                dimensions = {"1080p": (1920, 1080), "2K": (2560, 1440), "4K": (3840, 2160)}[res]
            else:
                dimensions = {"1080p": (1080, 1920), "2K": (1440, 2560), "4K": (2160, 3840)}[res]
            width, height = dimensions

            filters = [f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=30,format=yuv420p[v0]"]
            current = "v0"
            if self.show_titles.get():
                for i, path in enumerate(self.tracks):
                    start = starts[i]
                    end = start + durations[i]
                    label = f"vtitle{i}"
                    title = ff_escape(Path(path).stem)
                    filters.append(
                        f"[{current}]drawtext=text='{title}':font='Arial':fontcolor=white:fontsize=h*0.045:"
                        f"x=(w-text_w)/2:y=h*0.82:box=1:boxcolor=black@0.38:boxborderw=18:"
                        f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
                        f"enable='between(t,{start:.3f},{end:.3f})'[{label}]"
                    )
                    current = label
            filters.append(f"[{current}]null[vout]")

            audio_labels = []
            for i in range(len(self.tracks)):
                label = f"a{i}"
                filters.append(f"[{i+1}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[{label}]")
                audio_labels.append(label)

            if len(audio_labels) == 1:
                filters.append(f"[{audio_labels[0]}]anull[aout]")
            elif crossfade > 0:
                prev = audio_labels[0]
                for i in range(1, len(audio_labels)):
                    out = f"ax{i}"
                    filters.append(f"[{prev}][{audio_labels[i]}]acrossfade=d={crossfade:.3f}:c1=tri:c2=tri[{out}]")
                    prev = out
                filters.append(f"[{prev}]anull[aout]")
            else:
                joined = "".join(f"[{x}]" for x in audio_labels)
                filters.append(f"{joined}concat=n={len(audio_labels)}:v=0:a=1[aout]")

            output_name = "Video_Musik_Final.mp4"
            output_path = Path(self.output_dir.get()) / output_name
            cmd = [ffmpeg, "-y", "-stream_loop", "-1", "-i", self.video_path.get()]
            for p in self.tracks:
                cmd += ["-i", p]
            cmd += [
                "-filter_complex", ";".join(filters),
                "-map", "[vout]", "-map", "[aout]",
                "-t", f"{total:.3f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", str(output_path)
            ]
            self.events.put(("status", "Sedang membuat video… Jangan tutup aplikasi."))
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if result.returncode != 0:
                raise RuntimeError(result.stderr[-5000:] or "FFmpeg gagal memproses video.")

            if self.make_timestamps.get():
                stamp_path = Path(self.output_dir.get()) / "Penanda_Waktu_YouTube.txt"
                with open(stamp_path, "w", encoding="utf-8") as f:
                    f.write("Penanda Waktu YouTube\n\n")
                    for i, (p, start) in enumerate(zip(self.tracks, starts)):
                        f.write(f"{timecode(start)} {Path(p).stem}\n")
            playlist_path = Path(self.output_dir.get()) / "Daftar_Putar.m3u"
            with open(playlist_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for p in self.tracks:
                    f.write(str(Path(p).resolve()) + "\n")
            self.events.put(("done", str(output_path)))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self.status.set(value)
                elif kind == "done":
                    self.progress.stop()
                    self.rendering = False
                    self.status.set("Selesai! Video dan berkas pendukung sudah dibuat.")
                    messagebox.showinfo("Pembuatan video selesai", f"Video berhasil dibuat:\n{value}\n\nBerkas penanda waktu dan daftar putar juga tersimpan di folder tujuan.")
                elif kind == "error":
                    self.progress.stop()
                    self.rendering = False
                    self.status.set("Pembuatan video gagal. Periksa pesan kesalahan.")
                    messagebox.showerror("Pembuatan video gagal", value)
        except queue.Empty:
            pass
        self.root.after(150, self._poll_events)

if __name__ == "__main__":
    root = tk.Tk()
    app = MusicVideoStudio(root)
    root.mainloop()
