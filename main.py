import kivy
kivy.require('2.0.0')

import sys
import os

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.properties import ObjectProperty, NumericProperty, StringProperty, ListProperty
from kivy.factory import Factory
import json
import random
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.image import Image

# Fonction pour obtenir le chemin correct des fichiers (dev ou .exe)
def resource_path(relative_path):
    """Retourne le chemin correct pour un fichier, que ce soit en mode dev ou dans un .exe."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Gestion du chemin pour PyInstaller
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# Charger les fichiers KV avec le chemin correct
kv_file1 = os.path.join(base_path, 'qcm_design.kv')
kv_file2 = os.path.join(base_path, 'accueil_design.kv')
Builder.load_file(kv_file1)
Builder.load_file(kv_file2)

class QuestionScreen(Screen):
    question_text = StringProperty('')
    options = ListProperty([])
    correct_answers = ListProperty([])  # Liste des bonnes réponses
    score = NumericProperty(0)
    lives = NumericProperty(3)
    progress = NumericProperty(0)
    timer = NumericProperty(60)
    timer_text = StringProperty("60")
    remaining_questions_text = StringProperty("")

    def __init__(self, **kwargs):
        super(QuestionScreen, self).__init__(**kwargs)
        self.questions = []
        self.current_question_index = 0
        self.timer_event = None
        self.selected_options = []  # Stocke les options sélectionnées

    def on_enter(self):
        # self.load_questions() # Removed this line
        self.show_question()
        self.start_timer()
        self.update_lives()

    def update_lives(self):
        self.ids.lives_layout.clear_widgets()
        for _ in range(self.lives):
            heart = Image(source=resource_path('heart.png'), size_hint_x=None, width=45)
            self.ids.lives_layout.add_widget(heart)

    def load_questions(self, theme_name="questions"):
        # Chemin pour les thèmes dans le dossier de travail courant
        current_themes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes")

        # Chemin pour les thèmes inclus dans l'exécutable
        if getattr(sys, 'frozen', False):
            bundled_themes_path = os.path.join(sys._MEIPASS, "themes")
        else:
            bundled_themes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes")

        # Chemin pour les thèmes ajoutés par l'utilisateur
        user_themes_path = os.path.join(os.path.dirname(sys.executable), "themes")

        # Essaie d'abord le dossier de travail courant
        theme_file = os.path.join(current_themes_path, f"{theme_name}.json")
        if not os.path.exists(theme_file):
            # Essaie ensuite le dossier utilisateur
            theme_file = os.path.join(user_themes_path, f"{theme_name}.json")
            if not os.path.exists(theme_file):
                # Si le fichier n'est pas trouvé dans le dossier utilisateur, cherche dans les thèmes inclus
                theme_file = os.path.join(bundled_themes_path, f"{theme_name}.json")

        try:
            print(f"Loading theme file: {theme_file}")
            with open(theme_file, 'r', encoding='utf-8') as file:
                self.questions = json.load(file)
                random.shuffle(self.questions)
                self.current_question_index = 0
        except FileNotFoundError:
            print(f"Le fichier de thème {theme_file} est introuvable ! Chargement des questions par défaut.")
            self.load_default_questions()
        except json.JSONDecodeError:
            print(f"Erreur de format dans le fichier de thème {theme_file} est introuvable ! Chargement des questions par défaut.")
            self.load_default_questions()

    def load_default_questions(self):
        # Define default questions here or load from a default file
        self.questions = [
            {"question": "Question par défaut 1?", "options": ["Oui", "Non"], "correctIndices": [0]},
            {"question": "Question par défaut 2?", "options": ["Vrai", "Faux"], "correctIndices": [1]}
        ]
        random.shuffle(self.questions)
        self.current_question_index = 0

    def show_question(self):
        if self.current_question_index < len(self.questions):
            question_data = self.questions[self.current_question_index]
            self.question_text = question_data['question']
            self.options = question_data['options']
            self.correct_answers = [question_data['options'][i] for i in question_data['correctIndices']]
            self.progress = (self.current_question_index / len(self.questions)) * 100
            self.timer = 60
            self.timer_text = "60"
            self.remaining_questions_text = f"Il reste {len(self.questions) - self.current_question_index -1} questions"
            self.selected_options = []  # Réinitialise les sélections
            self.update_options()
        else:
            self.show_game_over()

    def update_options(self):
        self.ids.options_layout.clear_widgets()
        for option in self.options:
            button = Factory.OptionButton(
                text=option,
                font_size='16sp',
                on_press=self.toggle_selection  # Nouvelle fonction pour sélectionner/désélectionner
            )
            self.ids.options_layout.add_widget(button)
        # Ajouter le bouton "Valider"
        validate_button = Factory.OptionButton(
            text="Valider",
            font_size='16sp',
            background_color=(0.1, 0.7, 0.3, 1),  # Vert pour le bouton Valider
            on_press=self.check_answer
        )
        self.ids.options_layout.add_widget(validate_button)
        self.validate_button = validate_button  # Stocke la référence

    def toggle_selection(self, instance):
        option = instance.text
        if option in self.selected_options:
            self.selected_options.remove(option)
            instance.background_color = [0.2, 0.6, 0.86, 1]  # Retour à la couleur normale
        else:
            self.selected_options.append(option)
            instance.background_color = [0.5, 0.5, 0.5, 1]  # Gris pour indiquer la sélection
        print(f"Options sélectionnées : {self.selected_options}")

    def check_answer(self, instance):
        self.stop_timer()
        self.ids.options_layout.remove_widget(self.validate_button)  # Supprime le bouton
        # Vérifie si les réponses sélectionnées sont correctes
        if instance is not None:  # Gérer le cas où le timer expire
            correct_answers_set = set(self.correct_answers)
            selected_options_set = set(self.selected_options)
            
            num_differences = len(correct_answers_set.symmetric_difference(selected_options_set))

            if num_differences == 0:
                self.score += 1
            elif num_differences == 1:
                self.score += 0.5
            elif num_differences == 2:
                self.score += 0.2
            else:
                self.score += 0
        else:
            # Timer expired, count as incorrect
            self.score += 0

        # Colore les boutons selon la correction
        for button in self.ids.options_layout.children:
            if isinstance(button, Factory.OptionButton) and button.text != "Valider":
                if button.text in self.correct_answers:
                    button.background_color = [0, 0.6, 0, 1]  # Vert pour les bonnes réponses
                elif button.text in self.selected_options:
                    button.background_color = [1, 0, 0, 1]  # Rouge pour les mauvaises réponses sélectionnées

        if instance is not None:  # Gérer le cas où le timer expire
            if len(set(self.selected_options).symmetric_difference(set(self.correct_answers))) != 0:
                self.lives -= 1
                self.update_lives()  # Met à jour l'affichage des vies
                # Animation de secouement pour les mauvaises réponses
                for button in self.ids.options_layout.children:
                    if isinstance(button, Factory.OptionButton) and button.text in self.selected_options and button.text not in self.correct_answers:
                        anim = Animation(pos_hint={'x': 0.05}, duration=0.1) + Animation(pos_hint={'x': -0.05}, duration=0.1)
                        anim += Animation(pos_hint={'x': 0}, duration=0.1)
                        anim.repeat = 2
                        anim.start(button)
                if self.lives <= 0:
                    Clock.schedule_once(lambda dt: self.show_game_over(), 1)

        # Ajout du bouton "Continuer"
        continue_button = Factory.OptionButton(
            text="Continuer",
            font_size='16sp',
            background_color=(0.1, 0.7, 0.3, 1),  # Vert pour le bouton Continuer
            on_press=self.continue_to_next_question
        )
        self.ids.options_layout.add_widget(continue_button)

    def continue_to_next_question(self, instance):
        if self.lives <= 0:
            self.show_game_over()
        elif self.current_question_index < len(self.questions) - 1:
            self.next_question()
        else:
            self.show_game_over()

    def next_question(self):
        self.current_question_index += 1
        self.show_question()
        self.start_timer()

    def reset_question(self):
        self.show_question()
        self.start_timer()

    def start_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)

    def update_timer(self, dt):
        self.timer -= 1
        self.timer_text = str(self.timer)
        if self.timer <= 0:
            self.check_answer(None)  # Valide automatiquement si le temps est écoulé
            return False

    def stop_timer(self):
        if self.timer_event:
            self.timer_event.cancel()

    def show_game_over(self):
        self.manager.current = 'game_over'
        total_questions = len(self.questions)
        if total_questions > 0:  # Avoid division by zero
            final_score_out_of_20 = (self.score / total_questions) * 20
        else:
            final_score_out_of_20 = 0
        self.manager.get_screen('game_over').final_score = round(final_score_out_of_20, 2)  # Arrondi à 2 décimales
        self.stop_timer()

class HomeScreen(Screen):
    def on_enter(self):
        self.load_themes()
        welcome_anim = Animation(opacity=1, duration=1, t='in_out_quad')
        start_anim = Animation(opacity=1, duration=0.8, t='out_bounce')
        pulse_anim = Animation(background_color=(0.3, 0.7, 0.9, 1), duration=0.8, t='in_out_sine') + \
                     Animation(background_color=(0.2, 0.6, 0.86, 1), duration=0.8, t='in_out_sine')
        pulse_anim.repeat = True

        welcome_anim.start(self.ids.welcome_label)
        start_anim.start(self.ids.start_button)
        pulse_anim.start(self.ids.start_button)

    def load_themes(self):
        # Chemin pour les thèmes inclus dans l'exécutable (PyInstaller)
        if getattr(sys, 'frozen', False):
            bundled_themes_path = os.path.join(sys._MEIPASS, "themes")
        else:
            bundled_themes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes")

        # Chemin pour les thèmes ajoutés par l'utilisateur (à côté de l'exécutable)
        user_themes_path = os.path.join(os.path.dirname(sys.executable), "themes")

        # Crée le dossier user_themes_path s'il n'existe pas
        if not os.path.exists(user_themes_path):
            os.makedirs(user_themes_path)

        # Liste des fichiers JSON dans les deux dossiers
        bundled_themes = []
        user_themes = []

        # Thèmes inclus dans l'exécutable
        if os.path.exists(bundled_themes_path):
            bundled_themes = [f for f in os.listdir(bundled_themes_path) if f.endswith(".json")]

        # Thèmes ajoutés par l'utilisateur
        if os.path.exists(user_themes_path):
            user_themes = [f for f in os.listdir(user_themes_path) if f.endswith(".json")]

        # Combine les deux listes et supprime les doublons
        all_themes = list(set(bundled_themes + user_themes))
        theme_names = [f[:-5] for f in all_themes]  # Retire l'extension .json
        self.ids.theme_spinner.values = theme_names if theme_names else ["Aucun thème disponible"]

    def start_game(self, theme_file):
        if theme_file and theme_file != 'Choisir un thème' and theme_file != 'Aucun thème disponible':
            theme_name = theme_file # Ne pas ajouter l'extension .json
            question_screen = self.manager.get_screen('question')
            question_screen.load_questions(theme_name)
            question_screen.score = 0  # Réinitialisation du score
            question_screen.lives = 3 # Réinitialisation des vies
            self.manager.current = 'question'
        else:
            print("Veuillez choisir un thème de questions.")

class GameOverScreen(Screen):
    final_score = NumericProperty(0)

    def go_home(self):
        self.manager.current = 'home'

class QCMApp(App):
    def resource_path(self, relative_path):
        """Retourne le chemin correct pour un fichier, que ce soit en mode dev ou dans un .exe."""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(QuestionScreen(name='question'))
        sm.add_widget(GameOverScreen(name='game_over'))
        sm.current = 'home'
        return sm
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(HomeScreen(name='home'))  # Ajout de l'écran d'accueil
        sm.add_widget(QuestionScreen(name='question'))
        sm.add_widget(GameOverScreen(name='game_over'))
        sm.current = 'home'  # Définir l'écran d'accueil comme écran initial
        return sm

if __name__ == '__main__':
    QCMApp().run()
