import sys
import numpy as np
import sounddevice as sd
import soundfile as sf
import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QDial, QComboBox, QSlider, QLineEdit, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush, QPen, QRadialGradient
from scipy.signal import resample_poly

class VisualIndicator(QWidget):
    """Widget per l'animazione visiva dei battiti."""
    def __init__(self, num_beats=4, parent=None):
        super().__init__(parent)
        self.num_beats = num_beats
        self.current_beat = 0
        self.setFixedSize(400, 80)  # Dimensioni del widget (più larghe per ospitare più dots)

    def set_current_beat(self, beat):
        """Imposta il battito corrente e aggiorna l'animazione."""
        self.current_beat = beat
        self.update()  # Richiede un ridisegno del widget

    def paintEvent(self, event):
        """Disegna i punti e illumina quello corrente."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dimensioni e spaziatura dei punti
        dot_size = 30  # Dots più piccoli
        spacing = 10   # Spaziatura ridotta
        total_width = self.num_beats * dot_size + (self.num_beats - 1) * spacing
        start_x = (self.width() - total_width) // 2  # Centra i dots orizzontalmente
        start_y = (self.height() - dot_size) // 2    # Centra i dots verticalmente

        for i in range(self.num_beats):
            # Colore del punto: giallo per il battito corrente, grigio per gli altri
            if i == self.current_beat:
                gradient = QRadialGradient(0, 0, dot_size / 2)
                gradient.setColorAt(0, QColor(255, 223, 0))  # Giallo luminoso
                gradient.setColorAt(1, QColor(255, 191, 0))  # Giallo scuro
                brush = QBrush(gradient)
            else:
                brush = QBrush(QColor(100, 100, 100))  # Grigio scuro

            # Disegna il punto con ombreggiatura
            painter.setPen(QPen(QColor(50, 50, 50), 2))  # Bordo scuro
            painter.setBrush(brush)
            painter.drawEllipse(start_x + i * (dot_size + spacing), start_y, dot_size, dot_size)

class Metronome(QWidget):
    def __init__(self):
        super().__init__()

        # Definisci gli attributi
        self.bpm = 120
        self.time_signature = "4/4"  # Tempo musicale di default
        self.running = False
        self.current_beat = 0  # Per tracciare il battito corrente
        self.volume = 0.5  # Volume predefinito (50%)

        # Parametri dei suoni
        self.sample_rate = 44100  # Frequenza di campionamento
        self.click_sound = self.load_sound("assets/click.wav")  # Carica il suono base
        self.pitch_factor = 1.5  # Fattore di pitch per il suono accentuato
        self.accent_sound = self.apply_pitch(self.click_sound, self.pitch_factor)  # Genera il suono pitchato

        # Timer per il metronomo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick_metronome)

        # Widget per l'animazione visiva
        self.visual_indicator = VisualIndicator(num_beats=4)  # Inizialmente per 4/4

        self.init_ui()  # Inizializzazione dell'interfaccia grafica

    def load_sound(self, file_name):
        """Carica il file audio e lo converte in mono se necessario."""
        file_path = os.path.join(os.path.dirname(__file__), file_name)
        print(f"Loading sound from: {file_path}")
        try:
            sound, _ = sf.read(file_path, dtype='float32')
            # Se il file è stereo, convertilo in mono
            if len(sound.shape) > 1 and sound.shape[1] == 2:
                sound = np.mean(sound, axis=1)  # Converti in mono
            print(f"Sound loaded successfully: {sound.shape}")  # Debug
            return sound
        except Exception as e:
            print(f"Errore nel caricamento del file audio: {e}")
            return np.zeros(44100, dtype='float32')  # Restituisce un array vuoto in caso di errore

    def apply_pitch(self, sound, pitch_factor):
        """Applica un effetto di pitch al suono."""
        new_length = int(len(sound) / pitch_factor)
        pitched_sound = resample_poly(sound, new_length, len(sound))
        return pitched_sound.astype(np.float32)

    def init_ui(self):
        """Inizializza l'interfaccia grafica."""
        self.setWindowTitle("Metronomo Essenziale")
        self.setGeometry(100, 100, 400, 500)

        # Layout principale
        layout = QVBoxLayout()

        # Etichetta BPM
        self.bpm_label = QLabel(f"BPM: {self.bpm}", self)
        self.bpm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bpm_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(self.bpm_label)

        # Pomello per il tempo
        self.bpm_dial = QDial(self)
        self.bpm_dial.setMinimum(30)  # Valore minimo: 30 BPM
        self.bpm_dial.setMaximum(300)  # Valore massimo: 300 BPM
        self.bpm_dial.setValue(self.bpm)
        self.bpm_dial.setNotchesVisible(True)
        self.bpm_dial.setFixedSize(150, 150)  # Dimensioni più grandi
        self.bpm_dial.valueChanged.connect(self.update_bpm)
        layout.addWidget(self.bpm_dial, 0, Qt.AlignmentFlag.AlignHCenter)

        # Input manuale del BPM
        self.bpm_input = QLineEdit(self)
        self.bpm_input.setPlaceholderText("Inserisci BPM")
        self.bpm_input.setMaxLength(3)
        self.bpm_input.returnPressed.connect(self.update_bpm_from_input)
        layout.addWidget(self.bpm_input)

        # ComboBox per selezionare il tempo musicale
        self.time_signature_combo = QComboBox(self)
        self.time_signature_combo.addItems(["4/4", "3/4", "2/4", "6/8", "5/4", "7/8"])
        self.time_signature_combo.currentTextChanged.connect(self.update_time_signature)
        layout.addWidget(self.time_signature_combo)

        # Slider per il volume
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(int(self.volume * 100))
        self.volume_slider.valueChanged.connect(self.update_volume)
        layout.addWidget(QLabel("Volume:"))
        layout.addWidget(self.volume_slider)

        # Pulsante di start/stop
        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.toggle_metronome)
        layout.addWidget(self.start_button)

        # Aggiungi l'indicatore visivo
        layout.addWidget(self.visual_indicator)

        # Imposta il layout principale
        self.setLayout(layout)

    def update_bpm(self):
        """Aggiorna il BPM e la UI."""
        self.bpm = self.bpm_dial.value()
        self.bpm_label.setText(f"BPM: {self.bpm}")
        self.bpm_input.setText(str(self.bpm))  # Aggiorna l'input manuale
        self.update_timer_interval()

    def update_bpm_from_input(self):
        """Aggiorna il BPM dall'input manuale."""
        try:
            bpm = int(self.bpm_input.text())
            if 30 <= bpm <= 300:  # Limite di BPM tra 30 e 300
                self.bpm = bpm
                self.bpm_dial.setValue(bpm)
                self.bpm_label.setText(f"BPM: {self.bpm}")
                self.update_timer_interval()
            else:
                print("Inserisci un valore valido per il BPM (30-300).")
        except ValueError:
            print("Inserisci un valore numerico valido.")

    def update_time_signature(self, text):
        """Aggiorna il tempo musicale."""
        self.time_signature = text
        self.current_beat = 0  # Reset del battito
        beats_in_measure = int(self.time_signature.split('/')[0])
        self.visual_indicator.num_beats = beats_in_measure
        self.visual_indicator.set_current_beat(0)  # Resetta l'animazione
        print(f"Tempo musicale aggiornato a {self.time_signature}")

    def update_timer_interval(self):
        """Aggiorna l'intervallo del timer in base al BPM."""
        interval = int((60.0 / self.bpm) * 1000)  # Converti in millisecondi
        self.timer.setInterval(interval)

    def update_volume(self, value):
        """Aggiorna il volume."""
        self.volume = value / 100.0

    def toggle_metronome(self):
        """Avvia o ferma il metronomo."""
        if self.running:
            self.running = False
            self.start_button.setText("Start")
            self.timer.stop()
        else:
            self.running = True
            self.start_button.setText("Stop")
            self.current_beat = 0
            self.update_timer_interval()
            self.timer.start()

    def tick_metronome(self):
        """Riproduce il suono in base al battito corrente."""
        beats_in_measure = int(self.time_signature.split('/')[0])  # Numero di battiti per misura

        # Riproduci il suono
        if self.current_beat == 0:
            sound = self.accent_sound  # Suono pitchato per il primo battito
        else:
            sound = self.click_sound  # Suono normale

        # Applica il volume
        sound = sound * self.volume

        # Riproduci il suono in modalità non bloccante
        sd.play(sound, self.sample_rate, blocking=False)

        # Aggiorna l'animazione visiva
        self.visual_indicator.set_current_beat(self.current_beat)

        # Aggiorna il contatore dei battiti
        self.current_beat += 1
        if self.current_beat >= beats_in_measure:
            self.current_beat = 0  # Resetta al primo battito della misura


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Metronome()
    window.show()
    sys.exit(app.exec())