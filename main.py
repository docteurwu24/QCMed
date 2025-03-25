import kivy
kivy.require('2.0.0')

import sys
import os
import json
import random
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.properties import NumericProperty, StringProperty, ListProperty, ObjectProperty
from kivy.factory import Factory
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.image import Image

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

Builder.load_file(resource_path('qcm_design.kv'))
Builder.load_file(resource_path('accueil_design.kv'))

class QuestionScreen(Screen):
    question_text = StringProperty('')
    options = ListProperty([])
    correct_answers = ListProperty([])
    score = NumericProperty(0)
    lives = NumericProperty(3)
    progress = NumericProperty(0)
    timer = NumericProperty(60)
    timer_text = StringProperty("60")
    remaining_questions_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.questions = []
        self.current_question_index = 0
        self.timer_event = None
        self.selected_options = []

    def on_enter(self):
        if not self.questions:
            self.load_questions()
        self.show_question()
        self.start_timer()
        self.update_lives()

    def update_lives(self):
        self.ids.lives_layout.clear_widgets()
        for _ in range(self.lives):
            heart = Image(source=resource_path('heart.png'), size_hint_x=None, width=45)
            self.ids.lives_layout.add_widget(heart)

    def load_questions(self, theme_name="questions"):
        theme_file = resource_path(f"themes/{theme_name}.json")
        try:
            with open(theme_file, 'r', encoding='utf-8') as file:
                self.questions = json.load(file)
            print(f"Questions chargées depuis {theme_file}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Erreur chargement thème {theme_file}: {e}. Chargement des questions par défaut.")
            self.load_default_questions()

    def load_default_questions(self):
        self.questions = [
            {
                "question": "2+2=?",
                "options": ["3", "4", "5"],
                "correctIndices": [1],
                "correctAnswers": ["Ce n'est pas 3", "C'est 4", "Ce n'est pas 5"]
            }
        ]
        print("Questions par défaut chargées.")

    def show_question(self):
        if self.current_question_index < len(self.questions):
            question_data = self.questions[self.current_question_index]
            self.question_text = question_data['question']
            
            self.options = []
            for i, option in enumerate(question_data['options']):
                self.options.append({
                    'text': option,
                    'correction': question_data['correctAnswers'][i],
                    'original_index': i
                })
            
            random.shuffle(self.options)
            
            self.correct_answers = [opt['text'] for opt in self.options 
                                  if opt['original_index'] in question_data['correctIndices']]
            
            self.progress = (self.current_question_index / len(self.questions)) * 100
            self.timer = 60
            self.timer_text = "60"
            self.remaining_questions_text = f"Il reste {len(self.questions) - self.current_question_index - 1} questions"
            self.selected_options = []
            self.update_options()

    def update_options(self):
        self.ids.options_layout.clear_widgets()
        for option in self.options:
            option_layout = Factory.OptionLayout()
            button = Factory.OptionButton(text=option['text'], on_press=self.toggle_selection)
            correction_label = Factory.CorrectionLabel(text=option['correction'], opacity=0)
            
            option_layout.option_data = option
            option_layout.add_widget(button)
            option_layout.add_widget(correction_label)
            self.ids.options_layout.add_widget(option_layout)

        validate_button = Factory.OptionButton(
            text="Valider",
            font_size='16sp',
            background_color=(0.1, 0.7, 0.3, 1),
            on_press=self.check_answer
        )
        self.ids.options_layout.add_widget(validate_button)

    def toggle_selection(self, instance):
        option = instance.text
        if option in self.selected_options:
            self.selected_options.remove(option)
            instance.background_color = [0.2, 0.6, 0.86, 1]
        else:
            self.selected_options.append(option)
            instance.background_color = [0.5, 0.5, 0.5, 1]

    def check_answer(self, instance):
        self.stop_timer()
        
        question_data = self.questions[self.current_question_index]
        
        # Calculer le nombre de différences
        differences = 0
        
        # Compter les bonnes réponses non sélectionnées
        for correct in self.correct_answers:
            if correct not in self.selected_options:
                differences += 1
                
        # Compter les mauvaises réponses sélectionnées
        for selected in self.selected_options:
            if selected not in self.correct_answers:
                differences += 1
        
        # Attribution des points selon le système demandé
        if differences == 0:
            self.score += 1  # Réponse parfaite
        elif differences == 1:
            self.score += 0.5  # Une différence
        elif differences == 2:
            self.score += 0.2  # Deux différences
        # 0 point pour 3 différences ou plus
        
        # Gestion des vies : retirer un cœur si score = 0.2 ou 0 (donc differences >= 2)
        if differences >= 2 and instance is not None:  # Modification ici
            self.lives -= 1
            self.update_lives()
            if self.lives <= 0:
                Clock.schedule_once(lambda dt: self.show_game_over(), 1)
        
        # Mise à jour visuelle
        for option_layout in self.ids.options_layout.children[::-1]:
            if isinstance(option_layout, Factory.OptionLayout) and len(option_layout.children) == 2:
                button = option_layout.children[1]
                correction_label = option_layout.children[0]
                option_data = option_layout.option_data
                
                original_index = question_data['options'].index(option_data['text'])
                is_correct = original_index in question_data['correctIndices']
                
                if is_correct:
                    if option_data['text'] in self.selected_options:
                        button.background_color = [0, 0.6, 0, 1]  # Vert
                        correction_label.opacity = 1
                    else:
                        button.background_color = [0.5, 0.5, 0.5, 0.7]  # Gris
                        correction_label.opacity = 0.7
                else:
                    if option_data['text'] in self.selected_options:
                        button.background_color = [1, 0, 0, 1]  # Rouge
                        correction_label.opacity = 1
                    else:
                        button.background_color = [0.3, 0.3, 0.3, 0.7]  # Gris foncé
                        correction_label.opacity = 0.7

        for child in self.ids.options_layout.children[:]:
            if isinstance(child, Factory.OptionButton) and child.text == "Valider":
                self.ids.options_layout.remove_widget(child)

        continue_button = Factory.OptionButton(
            text="Continuer",
            font_size='16sp',
            background_color=(0.1, 0.7, 0.3, 1),
            on_press=self.continue_to_next_question
        )
        self.ids.options_layout.add_widget(continue_button)

    def continue_to_next_question(self, instance):
        self.current_question_index += 1
        if self.lives <= 0 or self.current_question_index >= len(self.questions):
            self.show_game_over()
        else:
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
            self.check_answer(None)
            return False

    def stop_timer(self):
        if self.timer_event:
            self.timer_event.cancel()

    def show_game_over(self):
        self.manager.current = 'game_over'
        total_questions = len(self.questions)
        # Calculer la moyenne et ramener sur 20
        final_score = (self.score / total_questions * 20) if total_questions > 0 else 0
        self.manager.get_screen('game_over').final_score = round(final_score, 2)
        self.stop_timer()

class HomeScreen(Screen):
    def on_enter(self):
        self.load_themes()
        Animation(opacity=1, duration=1).start(self.ids.welcome_label)
        Animation(opacity=1, duration=0.8, t='out_bounce').start(self.ids.start_button)

    def load_themes(self):
        themes_path = resource_path("themes")
        if not os.path.exists(themes_path):
            os.makedirs(themes_path)
        themes = [f[:-5] for f in os.listdir(themes_path) if f.endswith(".json")]
        self.ids.theme_spinner.values = themes if themes else ["Aucun thème disponible"]

    def start_game(self, theme_file):
        if theme_file and theme_file != 'Choisir un thème' and theme_file != 'Aucun thème disponible':
            question_screen = self.manager.get_screen('question')
            question_screen.load_questions(theme_file)
            question_screen.score = 0
            question_screen.lives = 5
            self.manager.current = 'question'

class GameOverScreen(Screen):
    final_score = NumericProperty(0)

    def go_home(self):
        question_screen = self.manager.get_screen('question')
        question_screen.score = 0
        question_screen.lives = 3
        question_screen.current_question_index = 0
        self.manager.current = 'home'

class QCMApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(QuestionScreen(name='question'))
        sm.add_widget(GameOverScreen(name='game_over'))
        return sm

if __name__ == '__main__':
    QCMApp().run()