import kivy
kivy.require('2.0.0') # Explicitly require Kivy 2.0.0

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.properties import ObjectProperty, NumericProperty, StringProperty, ListProperty
from kivy.factory import Factory
import json
import random
from kivy.clock import Clock
from kivy.animation import Animation  # Pour l'animation
from kivy.uix.image import Image

Builder.load_file('qcm_design.kv')
Builder.load_file('accueil_design.kv') # Charger le fichier de design de l'écran d'accueil

class QuestionScreen(Screen):
    question_text = StringProperty('')
    options = ListProperty([])
    correct_answers = ListProperty([])  # Liste des bonnes réponses
    score = NumericProperty(0)
    lives = NumericProperty(3)
    progress = NumericProperty(0)
    timer = NumericProperty(20)
    timer_text = StringProperty("20")

    def __init__(self, **kwargs):
        super(QuestionScreen, self).__init__(**kwargs)
        self.questions = []
        self.current_question_index = 0
        self.timer_event = None
        self.selected_options = []  # Stocke les options sélectionnées

    def on_enter(self):
        self.load_questions()
        self.show_question()
        self.start_timer()
        self.update_lives()

    def update_lives(self):
        self.ids.lives_layout.clear_widgets()
        for _ in range(self.lives):
            heart = Image(source='heart.png', size_hint_x=None, width=45)
            self.ids.lives_layout.add_widget(heart)

    def load_questions(self, theme_file="themes/questions.json"):
        try:
            with open(theme_file, 'r', encoding='utf-8') as file:
                self.questions = json.load(file)
                random.shuffle(self.questions)
                self.current_question_index = 0
        except FileNotFoundError:
            print(f"Le fichier {theme_file} est introuvable !")
        except json.JSONDecodeError:
            print(f"Erreur de format dans {theme_file} !")

    def show_question(self):
        if self.current_question_index < len(self.questions):
            question_data = self.questions[self.current_question_index]
            self.question_text = question_data['question']
            self.options = question_data['options']
            self.correct_answers = [question_data['options'][i] for i in question_data['correctIndices']]
            self.progress = (self.current_question_index / len(self.questions)) * 100
            self.timer = 20
            self.timer_text = "20"
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
        self.validate_button = validate_button # Stocke la référence

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
        self.ids.options_layout.remove_widget(self.validate_button) # Supprime le bouton
        # Vérifie si les réponses sélectionnées sont correctes
        if instance is not None: # Gérer le cas où le timer expire
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
                    button.background_color = [0, 1, 0, 1]  # Vert pour les bonnes réponses
                elif button.text in self.selected_options:
                    button.background_color = [1, 0, 0, 1]  # Rouge pour les mauvaises réponses sélectionnées

        if instance is not None: # Gérer le cas où le timer expire
          if len(set(self.selected_options).symmetric_difference(set(self.correct_answers))) != 0 :
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
        elif self.current_question_index < len(self.questions) -1:
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
        self.manager.get_screen('game_over').final_score = round(final_score_out_of_20, 2) # Arrondi à 2 décimales
        self.stop_timer()

import os

class HomeScreen(Screen):
    def on_enter(self):
        self.load_themes()
        welcome_anim = Animation(opacity=1, duration=1, t='in_out_quad') # Modifier la courbe d'animation du titre
        start_anim = Animation(opacity=1, duration=0.8, t='out_bounce') # Ajouter un délai et ajuster la durée
        pulse_anim = Animation(scale_x=1.1, scale_y=1.1, duration=0.5, t='in_out_sine') + Animation(scale_x=1, scale_y=1, duration=0.5, t='in_out_sine') # Animation de pulsation avec scale_x et scale_y
        pulse_anim.repeat = True # Répéter l'animation de pulsation

        # welcome_anim.start(self.ids.welcome_label)
        # start_anim.start(self.ids.start_button) # Commented out to avoid AttributeError
        # pulse_anim.start(self.ids.start_button.ids.start_button_scale) # Animer l'instruction Scale du bouton

        # Animation de pulsation de la couleur de fond du bouton
        pulse_anim = Animation(background_color=(0.3, 0.7, 0.9, 1), duration=0.8, t='in_out_sine') + \
                     Animation(background_color=(0.2, 0.6, 0.86, 1), duration=0.8, t='in_out_sine')
        pulse_anim.repeat = True
        pulse_anim.start(self.ids.start_button) # Démarrer l'animation sur le bouton

    def load_themes(self):
        themes_dir = "themes"
        theme_files = [f for f in os.listdir(themes_dir) if f.endswith(".json")]
        self.ids.theme_spinner.values = theme_files

    def start_game(self, theme_file):
        if theme_file and theme_file != 'Choisir un thème':
            self.manager.get_screen('question').load_questions(f"themes/{theme_file}")
            self.manager.current = 'question'
        else:
            print("Veuillez choisir un thème de questions.")


class GameOverScreen(Screen):
    final_score = NumericProperty(0)

class QCMApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(HomeScreen(name='home')) # Ajout de l'écran d'accueil
        sm.add_widget(QuestionScreen(name='question'))
        sm.add_widget(GameOverScreen(name='game_over'))
        sm.current = 'home' # Définir l'écran d'accueil comme écran initial
        return sm

if __name__ == '__main__':
    QCMApp().run()
