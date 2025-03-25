# --- START OF FILE main.py ---

import kivy
kivy.require('2.0.0') # Ensure correct Kivy version

import sys
import os
import json
import random
import requests # For making HTTP requests to the server
from kivy.app import App
from kivy.storage.jsonstore import JsonStore # For storing user preferences (like pseudo)
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, NoTransition
from kivy.properties import NumericProperty, StringProperty, ListProperty, ObjectProperty
from kivy.factory import Factory
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.image import Image
from kivy.utils import platform # For checking platform if needed later

# --- Helper Function for Resource Paths (Handles PyInstaller Bundling) ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

# --- Load Initial KV File (Splash Screen Only) ---
try:
    kv_path = resource_path('splash.kv')
    if os.path.exists(kv_path):
        Builder.load_file(kv_path)
        print(f"KV file loaded successfully: {kv_path}")
    else:
        print(f"Error: Splash KV file not found: {kv_path}")
        # Handle critical error - app cannot start without splash
        sys.exit(1)
except Exception as e:
    print(f"Error loading KV file splash.kv from {kv_path}: {str(e)}")
    sys.exit(1)

# --- Screens ---

class SplashScreen(Screen):
    """A simple screen displayed while the main app resources load."""
    def on_enter(self, *args):
        """Schedule the loading of main resources."""
        print("Entering SplashScreen, scheduling main resource loading.")
        Clock.schedule_once(self.load_main_resources, 0.1) # Short delay

    def load_main_resources(self, dt):
        """Loads the rest of the KV files and screens."""
        print("Loading main application resources...")
        app = App.get_running_app()
        app.load_app_resources()
        print("Main resources loaded. Switching to home screen.")
        # Use NoTransition for the first switch to avoid visual glitch
        self.manager.transition = NoTransition()
        self.manager.current = 'home'
        # Restore default transition for subsequent switches
        self.manager.transition = FadeTransition(duration=0.3)

class QuestionScreen(Screen):
    # Properties bound to the KV file
    question_text = StringProperty('')
    options = ListProperty([])          # List of dictionaries for options (text, correction, original_index)
    correct_answers = ListProperty([])  # List of correct option texts for the current question
    score = NumericProperty(0)
    lives = NumericProperty(3)          # Start with 3 lives
    progress = NumericProperty(0)       # Percentage progress through the quiz
    timer = NumericProperty(60)         # Seconds per question
    timer_text = StringProperty("60")   # Display text for the timer
    remaining_questions_text = StringProperty("") # Text like "X questions remaining"
    theme_name = StringProperty('')     # Name of the current theme (e.g., "Immunologie")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.questions = []             # List to hold all questions for the current theme
        self.current_question_index = 0 # Index of the question being displayed
        self.timer_event = None         # Kivy Clock event for the timer
        self.selected_options = []      # List to hold texts of options selected by the user

    def on_enter(self):
        """Called when the screen becomes active."""
        print(f"Entering QuestionScreen for theme: {self.theme_name}")
        # Reset state if needed (though done in HomeScreen's start_game usually)
        self.score = 0
        self.lives = 3 # Reset lives (adjust if you want them persistent across games)
        self.current_question_index = 0
        # Load questions ONLY if the theme has changed or questions are empty
        # The actual loading is now triggered by HomeScreen
        if not self.questions or self.questions[0].get('_theme_name') != self.theme_name:
             self.load_questions(self.theme_name)

        if self.questions:
            self.show_question()
            self.start_timer()
        else:
            print("Error: No questions loaded, returning to home.")
            # Optionally show a popup error
            self.manager.current = 'home'
        self.update_lives()

    def update_lives(self):
        """Updates the heart icons display based on the 'lives' property."""
        if self.ids.get('lives_layout'): # Check if the layout exists in KV
            self.ids.lives_layout.clear_widgets()
            heart_image_path = resource_path('heart.png') # Ensure heart.png is available
            if os.path.exists(heart_image_path):
                 for _ in range(int(self.lives)): # Ensure lives is treated as int for range
                    heart = Image(source=heart_image_path, size_hint_x=None, width=dp(30)) # Use dp for density independence
                    self.ids.lives_layout.add_widget(heart)
            else:
                print(f"Warning: Heart image not found at {heart_image_path}")
                # Add fallback text or placeholder if image is missing
                for _ in range(int(self.lives)):
                     placeholder = Factory.Label(text='<3', size_hint_x=None, width=dp(30), color=(1,0,0,1))
                     self.ids.lives_layout.add_widget(placeholder)
        else:
            print("Warning: 'lives_layout' not found in QuestionScreen IDs.")


    def load_questions(self, theme_name="questions"):
        """Loads questions from the JSON file corresponding to the theme."""
        self.questions = [] # Clear previous questions
        theme_file = resource_path(os.path.join("themes", f"{theme_name}.json"))
        print(f"Attempting to load questions from: {theme_file}")
        try:
            with open(theme_file, 'r', encoding='utf-8') as file:
                self.questions = json.load(file)
                # Add theme name to questions data for checking later if needed
                if self.questions:
                    self.questions[0]['_theme_name'] = theme_name
            print(f"Successfully loaded {len(self.questions)} questions for theme '{theme_name}'")
        except FileNotFoundError:
            print(f"Error: Theme file not found: {theme_file}. Loading default questions.")
            self.load_default_questions()
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {theme_file}: {e}. Loading default questions.")
            self.load_default_questions()
        except Exception as e:
            print(f"An unexpected error occurred loading {theme_file}: {e}. Loading default questions.")
            self.load_default_questions()

    def load_default_questions(self):
        """Loads a single default question if theme loading fails."""
        self.questions = [
            {
                "question": "What is 2 + 2?",
                "options": ["3", "4", "5", "Window"],
                "correctIndices": [1], # Index of "4"
                "correctAnswers": ["Incorrect", "Correct!", "Incorrect", "Incorrect"],
                "_theme_name": "Default" # Mark as default
            }
        ]
        self.theme_name = "Default"
        print("Default questions loaded.")

    def show_question(self):
        """Displays the current question and its options."""
        self.stop_timer() # Stop previous timer if any

        if self.current_question_index < len(self.questions):
            question_data = self.questions[self.current_question_index]

            # --- Input Validation for Question Data ---
            if not all(k in question_data for k in ('question', 'options', 'correctIndices', 'correctAnswers')):
                print(f"Error: Invalid question format at index {self.current_question_index}. Skipping.")
                # Skip this question and try the next one, or handle error differently
                self.current_question_index += 1
                Clock.schedule_once(lambda dt: self.show_question(), 0.1) # Schedule next question show
                return

            if len(question_data['options']) != len(question_data['correctAnswers']):
                 print(f"Error: Mismatch between options ({len(question_data['options'])}) and correctAnswers ({len(question_data['correctAnswers'])}) lengths at index {self.current_question_index}. Skipping.")
                 self.current_question_index += 1
                 Clock.schedule_once(lambda dt: self.show_question(), 0.1)
                 return
            # --- End Input Validation ---


            self.question_text = question_data['question']

            # Prepare options with their associated correction text and original index
            self.options = []
            for i, option_text in enumerate(question_data['options']):
                self.options.append({
                    'text': option_text,
                    'correction': question_data['correctAnswers'][i],
                    'original_index': i
                })

            # Shuffle the options for display
            random.shuffle(self.options)

            # Determine the correct answers based on shuffled options' original indices
            self.correct_answers = [opt['text'] for opt in self.options
                                  if opt['original_index'] in question_data['correctIndices']]

            # Update UI elements
            self.progress = ((self.current_question_index + 1) / len(self.questions)) * 100
            self.timer = 60  # Reset timer for the new question
            self.timer_text = "60"
            remaining_count = len(self.questions) - self.current_question_index - 1
            self.remaining_questions_text = f"Il reste {remaining_count} question{'s' if remaining_count != 1 else ''}"

            self.selected_options = []  # Clear previous selections
            self.update_options_ui()      # Refresh the buttons etc. in the UI
            self.start_timer()          # Start the timer for this question

        else:
            # No more questions
            print("End of questions reached.")
            self.show_game_over()


    def update_options_ui(self):
        """Clears and redraws the option buttons and the validate button."""
        if not self.ids.get('options_layout'):
             print("Error: 'options_layout' not found in QuestionScreen IDs.")
             return

        self.ids.options_layout.clear_widgets()
        for option_data in self.options:
            # Use Kivy Factory to create instances from KV rules
            # Assumes 'OptionLayout', 'OptionButton', 'CorrectionLabel' are defined in 'qcm_design.kv'
            try:
                option_layout = Factory.OptionLayout()
                # Button toggles selection
                button = Factory.OptionButton(text=option_data['text'])
                button.bind(on_press=self.toggle_selection)
                # Correction label (initially hidden)
                correction_label = Factory.CorrectionLabel(text=option_data['correction'], opacity=0)

                # Store data with the layout for later reference
                option_layout.option_data = option_data
                option_layout.add_widget(button)
                option_layout.add_widget(correction_label) # Add label even if hidden
                self.ids.options_layout.add_widget(option_layout)
            except Exception as e:
                print(f"Error creating option layout/widget for '{option_data.get('text')}': {e}")


        # Add the "Validate" button
        try:
            validate_button = Factory.OptionButton(
                text="Valider",
                font_size='16sp',
                background_color=(0.1, 0.7, 0.3, 1), # Greenish color
                on_press=self.check_answer # Call check_answer when pressed
            )
            # Add some margin/padding if needed via size_hint or pos_hint in KV or here
            self.ids.options_layout.add_widget(validate_button)
        except Exception as e:
            print(f"Error creating validate button: {e}")

    def toggle_selection(self, instance):
        """Handles selecting/deselecting an option button."""
        option_text = instance.text
        # Find the OptionLayout containing this button
        option_layout = instance.parent

        if option_text in self.selected_options:
            self.selected_options.remove(option_text)
            # Restore original button color (defined in KV or default)
            instance.background_color = Factory.OptionButton.background_color
            # Alternatively: instance.background_color = [0.2, 0.6, 0.86, 1] # Or your default color
        else:
            self.selected_options.append(option_text)
            instance.background_color = [0.5, 0.5, 0.5, 1] # Grey indicates selection

    def check_answer(self, instance):
        """Checks the selected answers against the correct ones and updates score/lives."""
        self.stop_timer() # Stop timer immediately

        # Ensure we have valid question data
        if self.current_question_index >= len(self.questions):
            print("Error: check_answer called with invalid question index.")
            return # Avoid index out of bounds

        question_data = self.questions[self.current_question_index]

        # Calculate differences (missed correct answers + selected incorrect answers)
        differences = 0
        correct_indices = question_data.get('correctIndices', []) # Indices from original options list

        # Using the shuffled self.options list:
        for opt_data in self.options:
            is_correct = opt_data['original_index'] in correct_indices
            is_selected = opt_data['text'] in self.selected_options

            if is_correct and not is_selected:
                differences += 1 # Missed a correct answer
            elif not is_correct and is_selected:
                differences += 1 # Selected an incorrect answer

        print(f"Question {self.current_question_index + 1}: Correct={self.correct_answers}, Selected={self.selected_options}, Differences={differences}")

        # Award points based on the number of differences
        score_increase = 0
        # --- FIX: Ensure 0 points if nothing is selected ---
        if not self.selected_options:
             score_increase = 0
             print("No options selected, score increase is 0.")
        # --- End FIX ---
        elif differences == 0:
            score_increase = 1.0  # Perfect answer
        elif differences == 1:
            score_increase = 0.5  # One mistake
        elif differences == 2:
            score_increase = 0.2  # Two mistakes
        # Else: score_increase remains 0 (3+ mistakes)

        self.score += score_increase
        print(f"Score increased by {score_increase}. Total score: {self.score}")

        # Deduct a life if 2 or more differences (score increase <= 0.2)
        if differences >= 2:
            self.lives -= 1
            print(f"Lost a life. Lives remaining: {self.lives}")
            self.update_lives()
            # Optionally add visual feedback for losing a life (e.g., screen flash red)
            if self.lives <= 0:
                print("No lives left. Game Over.")
                # Delay showing game over slightly to allow user to see feedback
                Clock.schedule_once(lambda dt: self.show_game_over(), 1.5)
                # Prevent further actions after losing last life
                self._disable_options_and_show_feedback(correct_indices)
                return # Exit check_answer early

        # Update button appearances and show correction labels
        self._disable_options_and_show_feedback(correct_indices)

        # Remove the "Validate" button (if it exists)
        if instance and instance.parent == self.ids.options_layout:
             self.ids.options_layout.remove_widget(instance)

        # Add the "Continue" button
        try:
            continue_button = Factory.OptionButton(
                text="Continuer",
                font_size='16sp',
                background_color=(0.1, 0.7, 0.3, 1), # Greenish
                on_press=self.continue_to_next_question
            )
            self.ids.options_layout.add_widget(continue_button)
        except Exception as e:
            print(f"Error creating continue button: {e}")


    def _disable_options_and_show_feedback(self, correct_indices):
        """Helper to update UI after validation: disable buttons, color code, show corrections."""
        if not self.ids.get('options_layout'): return

        for child in self.ids.options_layout.children:
            if isinstance(child, Factory.OptionLayout):
                button = child.children[1] # Assuming Button is second child added
                correction_label = child.children[0] # Assuming Label is first child added
                option_data = child.option_data

                # Disable the button
                button.disabled = True

                is_correct = option_data['original_index'] in correct_indices
                is_selected = option_data['text'] in self.selected_options

                anim_duration = 0.5 # Duration for feedback animations

                if is_correct:
                    if is_selected:
                        # Correct and selected: Bright Green, show correction
                        Animation(background_color=[0, 0.8, 0, 1], duration=anim_duration).start(button)
                        Animation(opacity=1, duration=anim_duration).start(correction_label)
                    else:
                        # Correct but not selected: Dim Green/Grey, show correction faintly
                        Animation(background_color=[0.2, 0.5, 0.2, 0.8], duration=anim_duration).start(button)
                        Animation(opacity=0.7, duration=anim_duration).start(correction_label)
                else: # Incorrect option
                    if is_selected:
                        # Incorrect and selected: Bright Red, show correction
                        Animation(background_color=[1, 0.1, 0.1, 1], duration=anim_duration).start(button)
                        Animation(opacity=1, duration=anim_duration).start(correction_label)
                    else:
                        # Incorrect and not selected: Dark Grey, hide correction (or show faintly if desired)
                        Animation(background_color=[0.3, 0.3, 0.3, 0.7], duration=anim_duration).start(button)
                        Animation(opacity=0, duration=anim_duration).start(correction_label) # Keep hidden


    def continue_to_next_question(self, instance):
        """Moves to the next question or ends the game."""
        # Remove the "Continue" button
        if instance and instance.parent == self.ids.options_layout:
             self.ids.options_layout.remove_widget(instance)

        self.current_question_index += 1

        if self.lives <= 0:
             # Should have already been caught, but as a safeguard
             self.show_game_over()
        elif self.current_question_index < len(self.questions):
             self.show_question() # Load and display the next question
        else:
             # Finished all questions
             self.show_game_over()


    def start_timer(self):
        """Starts the countdown timer for the current question."""
        self.stop_timer() # Ensure no duplicate timers
        self.timer = 60 # Reset time
        self.timer_text = str(self.timer)
        self.timer_event = Clock.schedule_interval(self.update_timer, 1) # Tick every second

    def update_timer(self, dt):
        """Decrements the timer and checks if time is up."""
        self.timer -= 1
        self.timer_text = str(self.timer)
        if self.timer <= 10:
            # Optional: Change timer color to red or add visual warning
            pass
        if self.timer <= 0:
            print("Time's up!")
            # Find the "Validate" button to pass to check_answer (or pass None)
            validate_button = None
            if self.ids.get('options_layout'):
                for widget in self.ids.options_layout.children:
                     if isinstance(widget, Factory.OptionButton) and widget.text == "Valider":
                          validate_button = widget
                          break
            self.check_answer(validate_button) # Automatically check answer with current selections
            return False # Stop the timer schedule

    def stop_timer(self):
        """Stops the currently active timer."""
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

    def show_game_over(self):
        """Transitions to the GameOverScreen and passes the final score."""
        self.stop_timer() # Make sure timer is stopped

        total_questions = len(self.questions) if self.questions else 1 # Avoid division by zero
        # Calculate final score out of 20
        final_score_raw = (self.score / total_questions) * 20
        final_score = round(final_score_raw, 2) # Round to 2 decimal places

        print(f"Game Over. Final Score (raw): {self.score}/{total_questions} -> (/20): {final_score}")

        # Get the GameOverScreen instance and set its properties
        if self.manager.has_screen('game_over'):
            game_over_screen = self.manager.get_screen('game_over')
            game_over_screen.final_score = final_score
            game_over_screen.theme_name = self.theme_name # Pass the theme name for leaderboard context
            self.manager.current = 'game_over' # Switch screen
        else:
            print("Error: 'game_over' screen not found in ScreenManager.")
            self.manager.current = 'home' # Fallback to home

        # Reset QuestionScreen state for the next game
        self.questions = []
        self.current_question_index = 0
        self.score = 0
        self.lives = 3


class HomeScreen(Screen):
    """The main menu screen where users choose a theme."""
    themes = ListProperty([]) # List of available theme names

    def on_enter(self):
        """Called when the screen becomes active. Schedule theme loading and animations."""
        # Schedule theme loading instead of doing it directly
        Clock.schedule_once(self.load_themes, 0.1) # Load themes shortly after screen appears (dt is passed automatically)

        # Simple fade-in animations for elements
        if self.ids.get('welcome_label'):
            self.ids.welcome_label.opacity = 0
            Animation(opacity=1, duration=1).start(self.ids.welcome_label)
        if self.ids.get('theme_spinner'):
            self.ids.theme_spinner.opacity = 0
            # Removed delay=0.2 from the spinner animation
            Animation(opacity=1, duration=1).start(self.ids.theme_spinner)
        if self.ids.get('start_button'):
            self.ids.start_button.opacity = 0
            # Removed delay=0.5 from the start_button animation
            Animation(opacity=1, duration=0.8, t='out_bounce').start(self.ids.start_button)

    def load_themes(self, dt): # Added dt argument for Clock.schedule_once
        """Loads theme names from the 'themes' directory."""
        themes_dir = resource_path("themes")
        default_text = "Choisir un thème"
        self.themes = [default_text] # Start with default prompt

        try:
            if not os.path.exists(themes_dir):
                print(f"Themes directory not found, creating: {themes_dir}")
                os.makedirs(themes_dir)

            # List .json files in the themes directory
            available_themes = [f[:-5] for f in os.listdir(themes_dir)
                                if f.endswith(".json") and os.path.isfile(os.path.join(themes_dir, f))]

            if available_themes:
                self.themes.extend(sorted(available_themes)) # Add sorted theme names
                print(f"Themes loaded: {available_themes}")
            else:
                print("No themes found in themes directory.")
                self.themes.append("Aucun thème disponible")

        except Exception as e:
            print(f"Error loading themes from {themes_dir}: {e}")
            self.themes.append("Erreur chargement thèmes")

        # Update the Spinner values
        if self.ids.get('theme_spinner'):
            self.ids.theme_spinner.values = self.themes
            self.ids.theme_spinner.text = default_text # Reset selection display
        else:
             print("Warning: 'theme_spinner' not found in HomeScreen IDs.")

    def start_game(self, selected_theme): # Pass theme explicitly
        """Starts the game with the selected theme."""
        # selected_theme = self.ids.theme_spinner.text # Already passed as argument

        # Validate selection
        if selected_theme in ("Choisir un thème", "Aucun thème disponible", "Erreur chargement thèmes", "Chargement des thèmes..."):
             print("Error: Cannot start game, theme spinner not found.")
             return

        selected_theme = self.ids.theme_spinner.text

        # Validate selection
        if selected_theme in ("Choisir un thème", "Aucun thème disponible", "Erreur chargement thèmes"):
            print("Invalid theme selected. Please choose a valid theme.")
            # Optional: Show a popup message to the user
            # anim = Animation(color=(1,0,0,1), duration=0.1) + Animation(color=(1,1,1,1), duration=0.1) # Flash spinner text red
            # anim.repeat = True
            # anim.start(self.ids.theme_spinner) # Doesn't work directly on text color easily, better with popup
            return

        print(f"Starting game with theme: {selected_theme}")

        # Get the QuestionScreen, set the theme, and switch to it
        if self.manager.has_screen('question'):
            question_screen = self.manager.get_screen('question')
            question_screen.theme_name = selected_theme
            # Ensure questions are loaded for the selected theme if not already
            # QuestionScreen's on_enter will handle this check
            # No need to load questions here, on_enter in QuestionScreen will handle it
            # Reset score/lives/index potentially (though on_enter does it too)
            question_screen.score = 0
            question_screen.lives = 3
            question_screen.current_question_index = 0
            self.manager.current = 'question'
        else:
            print("Error: 'question' screen not found.")

    def go_to_leaderboard(self):
        """Navigates to the leaderboard screen for the selected theme."""
        if not self.ids.get('theme_spinner'):
             print("Error: Cannot go to leaderboard, theme spinner not found.")
             return
        selected_theme = self.ids.theme_spinner.text

        if selected_theme in ("Choisir un thème", "Aucun thème disponible", "Erreur chargement thèmes"):
            print("Invalid theme selected for leaderboard.")
            # Add user feedback if desired
            return

        print(f"Navigating to leaderboard for theme: {selected_theme}")

        if self.manager.has_screen('leaderboard'):
            leaderboard_screen = self.manager.get_screen('leaderboard')
            leaderboard_screen.qcm_id = selected_theme # Set the theme ID for the leaderboard
            self.manager.current = 'leaderboard' # Switch screen
        else:
            print("Error: 'leaderboard' screen not found.")


class PseudoPopup(Popup):
    """Popup to ask for the user's pseudo after the game."""
    pseudo = StringProperty('')      # Bound to the TextInput in the popup's KV
    theme_name = StringProperty('')  # To know which QCM the score belongs to
    callback = ObjectProperty(None)  # Function to call when 'OK' is pressed

    def on_open(self):
        """Focus the text input when the popup opens."""
        Clock.schedule_once(self.focus_input, 0.1) # Small delay might be needed

    def focus_input(self, dt):
        """Sets focus on the pseudo input field."""
        if self.ids.get('pseudo_input'):
            self.ids.pseudo_input.focus = True
        else:
            print("Warning: 'pseudo_input' not found in PseudoPopup IDs.")

    def submit_pseudo(self):
        """Validates pseudo and calls the callback function."""
        entered_pseudo = self.ids.pseudo_input.text.strip() # Get text and remove whitespace
        if entered_pseudo:
            if self.callback:
                self.callback(entered_pseudo, self.theme_name) # Pass pseudo and theme
            self.dismiss() # Close the popup
        else:
            # Optional: Show an error message within the popup or shake animation
            print("Pseudo cannot be empty.")
            # Simple visual feedback: briefly change background
            # anim = Animation(background_color=(0.8,0,0,0.5), duration=0.1) + Animation(background_color=(0,0,0,0.8), duration=0.1) # Needs background defined in KV
            # anim.start(self.ids.popup_layout) # Assuming popup content has id 'popup_layout'


class LeaderboardScreen(Screen):
    """Screen to display high scores for a specific QCM theme."""
    qcm_id = StringProperty('')         # The theme name (e.g., "Immunologie")
    leaderboard_data = ListProperty([]) # List of score dictionaries [{'rank': ?, 'pseudo': ?, 'score': ?}]

    def on_enter(self):
        """Called when the screen is displayed. Loads the leaderboard."""
        print(f"Entering LeaderboardScreen for QCM ID: {self.qcm_id}")
        self.load_leaderboard()

    def load_leaderboard(self):
        """Fetches leaderboard data from the server."""
        # Clear previous data and indicate loading (optional but good practice)
        self.leaderboard_data = []
        if hasattr(self.ids, 'status_label'): # Check if status label exists
            self.ids.status_label.text = "Chargement du classement..." # Defined in leaderboard.kv

        print(f"Attempting to load leaderboard for QCM ID: {self.qcm_id}")
        if not self.qcm_id:
            print("Error: qcm_id is not set for LeaderboardScreen.")
            if hasattr(self.ids, 'status_label'):
                self.ids.status_label.text = "Erreur: ID du QCM manquant."
            return

        # --- Make Request to Server ---
        server_url = f'http://127.0.0.1:5000/leaderboard/{self.qcm_id}' # Use f-string
        try:
            response = requests.get(server_url, timeout=10) # Add a timeout
            print(f"Server response status code for {self.qcm_id}: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Server response JSON for {self.qcm_id}: {data}")
                    if isinstance(data, list):
                        self.leaderboard_data = data # Assign data to the ListProperty
                        if not data:
                            print(f"Leaderboard for {self.qcm_id} is empty.")
                            if hasattr(self.ids, 'status_label'):
                                self.ids.status_label.text = "Aucun score enregistré pour ce thème."
                        else:
                             if hasattr(self.ids, 'status_label'):
                                self.ids.status_label.text = "" # Clear status on success
                    else:
                        print(f"Error: Server returned unexpected data type: {type(data)}")
                        if hasattr(self.ids, 'status_label'):
                            self.ids.status_label.text = "Erreur: Réponse inattendue du serveur."
                except ValueError: # Includes json.JSONDecodeError
                     print(f"Error: Failed to decode JSON response from server for {self.qcm_id}.")
                     print(f"Response text: {response.text}")
                     if hasattr(self.ids, 'status_label'):
                        self.ids.status_label.text = "Erreur: Données du serveur invalides."
            else:
                # Handle non-200 HTTP responses
                print(f"Error: Server returned status code {response.status_code} for {self.qcm_id}")
                print(f"Response text: {response.text}")
                if hasattr(self.ids, 'status_label'):
                    self.ids.status_label.text = f"Erreur serveur ({response.status_code})."

        except requests.exceptions.Timeout:
            print(f"Error: Request timed out connecting to {server_url}.")
            if hasattr(self.ids, 'status_label'):
                self.ids.status_label.text = "Erreur: Délai de connexion dépassé."
        except requests.exceptions.ConnectionError:
            print(f"Error: Could not connect to the server at {server_url}.")
            if hasattr(self.ids, 'status_label'):
                self.ids.status_label.text = "Erreur: Impossible de joindre le serveur."
        except requests.exceptions.RequestException as e:
            # Catch other potential requests errors
            print(f"An unexpected network error occurred for {self.qcm_id}: {e}")
            if hasattr(self.ids, 'status_label'):
                self.ids.status_label.text = f"Erreur réseau inconnue: {e}"

        # --- Refresh RecycleView ---
        # Explicitly tell the RecycleView to refresh itself with the (potentially updated) data
        # This helps if the automatic binding doesn't trigger reliably
        if hasattr(self.ids, 'rv'):
            self.ids.rv.data = self.leaderboard_data
            # self.ids.rv.refresh_from_data() # Call this if direct data assignment isn't enough
            print(f"RecycleView data updated. Item count: {len(self.ids.rv.data)}")
        else:
             print("Warning: RecycleView with id 'rv' not found in LeaderboardScreen.")

    def go_back(self):
        """Navigate back, typically to the home screen."""
        # Clear data when leaving? Optional.
        # self.leaderboard_data = []
        self.manager.current = 'home'


class GameOverScreen(Screen):
    """Screen displayed when the game ends (lives=0 or all questions answered)."""
    final_score = NumericProperty(0)    # The calculated score (/20)
    theme_name = StringProperty('')     # The theme of the completed quiz
    store = JsonStore(resource_path('prefs.json')) # Store for user preferences

    def on_enter(self):
        """Shows the final score and prompts for pseudo."""
        print(f"Entering GameOverScreen. Score: {self.final_score}, Theme: {self.theme_name}")
        # Retrieve the last used pseudo from storage correctly
        last_pseudo = '' # Default value
        if self.store.exists('user_prefs'):
            user_prefs = self.store.get('user_prefs')
            last_pseudo = user_prefs.get('last_pseudo', '') # Use dict.get() here
        print(f"Retrieved last pseudo: '{last_pseudo}'")

        # Create and open the PseudoPopup
        try:
            popup = PseudoPopup(
                pseudo=last_pseudo,
                theme_name=self.theme_name,
                callback=self.send_score_to_server # Function to call after getting pseudo
            )
            popup.open()
        except Exception as e:
             print(f"Error creating or opening PseudoPopup: {e}")
             # Fallback if popup fails? Maybe just go home?
             # Clock.schedule_once(lambda dt: self.go_home(), 1)

    def send_score_to_server(self, pseudo, qcm_id):
        """Sends the validated pseudo and score to the Flask server."""
        print(f"Attempting to send score: Pseudo='{pseudo}', QCM_ID='{qcm_id}', Score={self.final_score}")

        # --- Save the pseudo locally for next time ---
        try:
            self.store.put('user_prefs', last_pseudo=pseudo)
            print(f"Saved pseudo '{pseudo}' to local store.")
        except Exception as e:
             print(f"Error saving pseudo to JsonStore: {e}")

        # --- Prepare data for server ---
        score_data = {
            'pseudo': pseudo,
            'qcm_id': qcm_id,
            'score': self.final_score # Send the score (/20)
        }

        # --- Make POST request to server ---
        server_url = 'http://127.0.0.1:5000/add_score'
        try:
            response = requests.post(server_url, json=score_data, timeout=10)
            print(f"Server response status code for add_score: {response.status_code}")
            try:
                response_json = response.json()
                print(f"Server response JSON: {response_json}")
                # Optional: Display server message (e.g., "Score updated!") in the UI briefly
                message = response_json.get('message', 'Statut inconnu.')
                # e.g., self.ids.server_message_label.text = message
                # Clock.schedule_once(lambda dt: setattr(self.ids.server_message_label, 'text', ''), 5) # Clear after 5s
            except ValueError: # Includes json.JSONDecodeError
                print("Error: Failed to decode JSON response from add_score.")
                print(f"Response text: {response.text}")
                # Optional: Display generic error in UI
                # self.ids.server_message_label.text = "Erreur serveur (données)."
            if response.status_code >= 400: # Handle HTTP errors (4xx, 5xx)
                 print(f"Server returned an error: {response.status_code} - {response.text}")
                 # Optional: Display error in UI
                 # self.ids.server_message_label.text = f"Erreur serveur ({response.status_code})."

        except requests.exceptions.Timeout:
            print(f"Error: Request timed out sending score to {server_url}.")
            # Optional: Display error in UI
            # self.ids.server_message_label.text = "Erreur: Délai dépassé (envoi score)."
        except requests.exceptions.ConnectionError:
            print(f"Error: Could not connect to the server at {server_url} to send score.")
            # Optional: Display error in UI
            # self.ids.server_message_label.text = "Erreur: Serveur inaccessible (envoi score)."
        except requests.exceptions.RequestException as e:
            print(f"An unexpected network error occurred sending score: {e}")
            # Optional: Display error in UI
            # self.ids.server_message_label.text = "Erreur réseau (envoi score)."


    def go_home(self):
        """Returns to the main home screen."""
        print("Returning to home screen from Game Over.")
        self.manager.current = 'home'

    def retry_theme(self):
        """Restarts the game with the same theme."""
        print(f"Retrying theme: {self.theme_name}")
        if self.manager.has_screen('question'):
            question_screen = self.manager.get_screen('question')
            question_screen.theme_name = self.theme_name
            # Reset necessary fields (on_enter will also run)
            question_screen.score = 0
            question_screen.lives = 3
            question_screen.current_question_index = 0
            self.manager.current = 'question'
        else:
            print("Error: 'question' screen not found for retry.")
            self.go_home() # Fallback


# --- Main Application Class ---

class QCMApp(App):
    """The main Kivy application class."""
    sm = None # Keep a reference to the screen manager

    def build(self):
        """Builds the Screen Manager and adds only the SplashScreen initially."""
        # Use a transition between screens (will be restored after splash)
        self.sm = ScreenManager(transition=FadeTransition(duration=0.3))

        # Add only the SplashScreen initially
        try:
            self.sm.add_widget(SplashScreen(name='splash'))
            print("SplashScreen added to ScreenManager successfully.")
        except Exception as e:
             print(f"Error adding SplashScreen to ScreenManager: {e}")
             return None # Indicate build failure

        return self.sm

    def load_app_resources(self):
        """Loads main KV files and adds main screens to the ScreenManager."""
        print("Executing load_app_resources...")
        # --- Load Remaining KV Files ---
        kv_files_to_load = ['qcm_design.kv', 'accueil_design.kv', 'popup_pseudo.kv', 'leaderboard.kv']
        for kv_file in kv_files_to_load:
            kv_path = resource_path(kv_file)
            try:
                if os.path.exists(kv_path):
                    Builder.load_file(kv_path)
                    print(f"KV file loaded successfully: {kv_path}")
                else:
                    print(f"Error: KV file not found: {kv_path}")
                    # Consider non-critical error handling
            except Exception as e:
                print(f"Error loading KV file {kv_file} from {kv_path}: {str(e)}")
                # Consider non-critical error handling

        # --- Add Main Screens ---
        try:
            if not self.sm.has_screen('home'):
                self.sm.add_widget(HomeScreen(name='home'))
            if not self.sm.has_screen('question'):
                self.sm.add_widget(QuestionScreen(name='question'))
            if not self.sm.has_screen('game_over'):
                self.sm.add_widget(GameOverScreen(name='game_over'))
            if not self.sm.has_screen('leaderboard'):
                self.sm.add_widget(LeaderboardScreen(name='leaderboard'))
            print("Main screens added to ScreenManager.")
        except Exception as e:
             print(f"Error adding main screens to ScreenManager: {e}")
             # Handle error, maybe show a popup

    def on_stop(self):
        """Called when the application is closed."""
        print("QCM App stopping.")
        # Perform any cleanup here if needed


# --- Entry Point ---

if __name__ == '__main__':
    # Set window size (optional)
    # from kivy.config import Config
    # Config.set('graphics', 'width', '400')
    # Config.set('graphics', 'height', '700')

    # Use density-independent pixels for sizing
    from kivy.metrics import dp

    # Run the application
    try:
        QCMApp().run()
    except Exception as e:
        print(f"An unhandled error occurred during app execution: {e}")
        # Log the error to a file or show a crash dialog
        # import traceback
        # traceback.print_exc() # Print detailed traceback
        # Consider using a more robust error reporting mechanism

# --- END OF FILE main.py ---
