import argparse
import re
import time
from os import path

import numpy as np
import pygame
from pygame import mixer

from utils import draw_score

FRET_HEIGHT = 256
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 720
# TODO: com TICKS_PER_UPDATE = 1 ta quebrando
TICKS_PER_UPDATE = 5
MS_PER_MIN = 60000

# TODO: qdo aumenta mto, da errado (ex 500)
PIXELS_PER_BEAT = 400
# PIXELS_PER_BEAT -> best offset
# 200 -> 600
# 20 -> 850

color_x_pos = [163, 227, 291, 355, 419]

# global_speed = 1
game_is_running = True


class Score():
    def __init__(self, decrease_mode=False):
        self.value = 0
        self.x_pos = SCREEN_WIDTH - 100
        self.font_size = 25
        self.decrease_mode = decrease_mode

        # The ammount of notes correctly hit in a row
        self._counter = 0

        self.rock_meter = 50

    def hit(self, value=10):
        self._counter = min(self._counter + 1, 39)
        self.value += value * self.multiplier

        self.rock_meter = min(self.rock_meter + 2, 100)

    def miss(self):
        self._counter = 0

        self.rock_meter -= 2
        if self.rock_meter <= 0:
            raise NotImplementedError("Game lost, rock meater -> 0")

    def miss_click(self):
        self.miss()
        self.value -= 10 * self.decrease_mode

    @property
    def counter(self):
        return self._counter + 1

    @property
    def multiplier(self):
        return 1 + self._counter // 10


def draw_score_multiplier(score, surface, x_pos=0, y_pos=0, size=25):
    # code slightly modified from draw score
    font = pygame.font.Font(
        pygame.font.match_font('arial'), size)

    value = score.multiplier
    color = ((255, 255, 255),  # white for x1
             (255, 255, 0),  # yellow for x2
             (0, 255, 0),  # green for x3
             (200, 0, 200)  # purple for x4
             )[value - 1]

    multiplier = font.render(f"x{value}", True, color)

    multiplier_rect = multiplier.get_rect()
    multiplier_rect.midtop = (x_pos, y_pos)
    screen.blit(multiplier, multiplier_rect)


def draw_rock_meter(score, surface, x_pos=0, y_pos=0):
    height = 10
    width = 20

    # draws the first layer of the meeter,
    # which consists of the 3 colors, but darkened
    for i in range(3):
        pygame.draw.rect(
            surface,
            (200 * (i < 2), 180 * (i > 0), 0),
            (x_pos + i*width, y_pos, width, height)
        )

    # highlits the color the meeter is in, as if it light up
    lightned_bar = int((score.rock_meter-1) * (3 / 100))
    pygame.draw.rect(
        surface,
        (255 * (lightned_bar < 2), 255 * (lightned_bar > 0), 0),
        (x_pos + lightned_bar*width, y_pos, width, height)
    )

    # locating the position on which the bar will be:
    total_size = width * 3
    place = x_pos + (score.rock_meter / 100) * total_size

    # drawing the bar on top of meeter
    pygame.draw.line(
        surface,
        color=(255, 255, 255),
        start_pos=(place, y_pos - 5),
        end_pos=(place, y_pos + height + 5),
        width=3
    )


class Note(pygame.sprite.Sprite):
    def __init__(self, song, imgs, start=0, note_type='N', color=None, duration=0):
        if color is None:
            raise TypeError("missing required argumet on note: color")
        elif not note_type in ('N', 'S'):
            raise TypeError("note_type must be 'N' or 'S'")

        super().__init__()
        self.start = int(start)
        self.type = 0 if note_type == 'N' else 1   # 0 = normal note, 1 = star
        self.color = int(color)
        self.duration = int(duration)

        self.__set_image(imgs, self.color)
        self.last_ticks = 0

        self.rect.x = color_x_pos[self.color]

        # note_beat = (note.start / float(song.resolution))# + song.offset
        # TODO: lembrar de levar em consideração o offset
        #print("NOTE BEAT:", note_beat)
        #pixels_per_beat = (song.bpm / 60.0) * 360
        #print("PPB:", pixels_per_beat)
        #note.y_pos = (- (note_beat * pixels_per_beat)) / song.divisor
        #print("Y:", note.y_pos)
        # TODO: Decide best way to start note's y values
        #note.y_pos = -(300 * note.start // song.resolution)
        self.y_pos = -(PIXELS_PER_BEAT * (self.start +
                                          song.offset) / song.resolution)

    def __repr__(self):
        return f'<Note start:{self.start} type:{self.type} color:{self.color} duration:{self.duration}>'

    def __str__(self):
        return f'Note: start={self.start}, type={self.type}, color={self.color}, duration={self.duration}'

    def __set_image(self, imgs, color):
        self.image = imgs[color + self.type * 5]
        self.image = pygame.transform.scale(self.image, (60, 60))
        self.rect = self.image.get_rect()

    def update(self, to_kill=None):
        self.rect.y = int(self.y_pos) + (SCREEN_HEIGHT-90)
        self.y_pos += (TICKS_PER_UPDATE * PIXELS_PER_BEAT / song.resolution)

        if self.rect.y > SCREEN_HEIGHT + 60 or to_kill == True:
            self.kill()


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "chart_file",
        help="Path to .CHART file.")
    parser.add_argument('-d', '--decrease_score', action='store_true',
                        help='enables the feature of decreasing the score for mistakes.')
    parser.add_argument('--human', action='store_true',
                        help='enables human controls through keyboard.')
    return parser.parse_args()


def load_imgs():
    imgs = []

    colors = ['green', 'red', 'yellow', 'blue', 'orange']
    for name in colors:
        sprite = pygame.image.load(
            path.join('..', 'assets', name + 'button.png')).convert_alpha()
        imgs.append(sprite)

    for name in colors:
        sprite = pygame.image.load(
            path.join('..', 'assets', name + 'star.png')).convert_alpha()
        imgs.append(sprite)

    return imgs


def create_button_list(imgs, buttons_sprites_list):
    buttons = []

    for i in range(5):
        button = create_button(imgs[i], color_x_pos[i])
        buttons.append(button)
        buttons_sprites_list.add(button)

    return buttons


def create_button(img, x_pos):
    button = pygame.sprite.Sprite()
    button.image = pygame.transform.scale(img, (60, 60))
    button.rect = button.image.get_rect()
    button.rect.y = SCREEN_HEIGHT-90
    button.rect.x = x_pos
    return button


class Song():
    def __init__(self):
        self.offset = 0
        self.resolution = 192
        self.bpm = 120  # Must be read from chart on [SyncTrack]
        self.divisor = 3
        self.name = ''
        self.guitar = ''
        self.bpm_dict = {}  # Should be a matrix
        self.ts = 4
        self.ts_dict = {}  # Should be a matrix


def load_chart(filename, imgs):

    f = open(filename, 'r')
    chart_data = f.read().replace('  ', '')
    f.close()

    song = load_song_info(chart_data)
    notes = load_notes(chart_data, song, imgs)

    return song, notes


def load_song_info(chart_data):

    search_string = '[Song]\n{\n'
    inf = chart_data.find(search_string)
    sup = chart_data[inf:].find('}')
    sup += inf
    inf += len(search_string)

    song_data = chart_data[inf:sup]

    song = Song()

    for line in song_data.splitlines():
        info = line.split()

        if (info[0] == 'Offset'):
            song.offset = int(info[2]) + 600

        if (info[0] == 'Resolution'):
            song.resolution = int(info[2])

        if (info[0] == 'MusicStream'):
            song.name = info[2].strip('\"')

        if (info[0] == 'GuitarStream'):
            song.guitar = info[2]

    load_resolutions(chart_data, song)
    return song


def load_resolutions(chart_data, song):
    search_string = '[SyncTrack]\n{\n'
    inf = chart_data.find(search_string)
    sup = chart_data[inf:].find('}')
    sup += inf
    inf += len(search_string)

    resolutions_data = chart_data[inf:sup]

    for line in resolutions_data.splitlines():
        res = line.split()

        if res[2] == 'B':
            song.bpm_dict[int(res[0])] = int(res[3])/1000
        elif res[2] == 'TS':
            song.ts_dict[int(res[0])] = int(res[3])

    song.bpm = song.bpm_dict[0]
    song.ts = song.ts_dict[0]


def load_notes(chart_data, song, imgs, difficulty='ExpertSingle'):

    search_string = "[" + difficulty + "]\n{\n"
    inf = chart_data.find(search_string)
    sup = chart_data[inf:].find('}')
    sup += inf
    inf += len(search_string)

    notes_data = chart_data[inf:sup]

    # pattern of the data for each note line
    #                   time    /  type / color / duration
    prog = re.compile("([0-9]+) = ([NS]) ([0-4]) ([0-9]+)")
    # time -> when the note is supposed to be played
    # type -> either normal or a star
    # color -> green, red, yellow, blue or orange.
    #           it has 0-4 so it gets only those 5 notes.
    #           If desired, can be set 0-6 to have all 7 notes in the sheet
    #           however, it requires the rest of the system to handle more
    #           note possibilities
    # duration -> allows to have any integer number as value.
    #           Could check on re docs to figure out a maximum number of characters.

    # getting all line's data parsed
    lines = prog.findall(notes_data)

    # using list comprehension to create a list of all the notes
    # and parsing the required information to the Note constructor
    notes = [Note(song, imgs, *line) for line in lines]

    return notes


def handle_inputs():
    keys = 'asdfg'  # could be a list, tuple or dict instead
    actions = [False, False, False, False, False]
    for event in pygame.event.get():

        if event.type == pygame.KEYDOWN:
            for n, l in enumerate(keys):
                if event.key == getattr(pygame, f"K_{l}"):
                    actions[n] = True
                else:
                    actions[n] = False

            print(actions)
    return actions


def render(screen, render_interval, score):
    # Draw Phase
    screen.fill((0, 0, 0))

    # draw guitar neck
    pygame.draw.rect(screen, (50, 50, 50), (160, 0, 320, SCREEN_HEIGHT))

    # draw neck borders
    pygame.draw.rect(screen, (200, 200, 200), (140, 0, 20, SCREEN_HEIGHT))
    pygame.draw.rect(screen, (200, 200, 200), (480, 0, 20, SCREEN_HEIGHT))

    for i in range(500):
        y_offset = (i * PIXELS_PER_BEAT)
        pygame.draw.rect(screen, (180, 180, 180),
                         (160, SCREEN_HEIGHT-y_offset-60-2, 320, 4))
        pygame.draw.rect(screen, (100, 100, 100),
                         (160, SCREEN_HEIGHT-y_offset+128-60-2, 320, 4))

    # draw Notes and Buttons
    buttons_sprites_list.draw(screen)
    visible_notes_list.draw(screen)
    # draw score
    draw_score(screen, str(score.value), score.font_size, score.x_pos)

    draw_rock_meter(score, screen, x_pos=score.x_pos, y_pos=600)

    draw_score_multiplier(score, screen, x_pos=100, y_pos=600)

    pygame.display.flip()

    return


recent_note_history = []
# TODO: separar handle input do update


def update(score, ticks, action):
    global game_is_running, recent_note_history

    # Poorly updates song BPM and TS values
    if ticks in song.bpm_dict:
        song.bpm = song.bpm_dict[ticks]
    if ticks in song.ts_dict:
        song.ts = song.ts_dict[ticks]

    # Add the first 50 notes to the "visible" notes list (the ones that will be rendered)
    visible_notes_list.add(all_notes_list.sprites()[50::-1])

    # Check for collisions
    Buttons_hit_list_by_color = [
        pygame.sprite.spritecollide(
            button_type,
            visible_notes_list,
            False,
            pygame.sprite.collide_circle_ratio(0.6)
        ) for button_type in Buttons]

    # Unoptimized unpressed notes detection:
    Buttons_hit_list = []
    for button_color in Buttons_hit_list_by_color:
        Buttons_hit_list += button_color

    for note in Buttons_hit_list:
        if not note in recent_note_history:
            recent_note_history.append(note)

    for note in recent_note_history:
        if not note in Buttons_hit_list:

            score.miss()

            recent_note_history.remove(note)
    # Finished unoptimized unpressed notes detection:

    # keys = 'asdfg'  # could be a list, tuple or dict instead
    # for event in pygame.event.get():
    for i in range(len(action)):

        # if event.type == pygame.QUIT:
        #     game_is_running = False

        # if event.type == pygame.KEYDOWN:
        # if action[i]:
        for n, notes_in_hit_zone in enumerate(Buttons_hit_list_by_color):
            # Eg: event.key == pygame.K_a
            # if event.key == getattr(pygame, f"K_{keys[n]}"):
            if action[i] and i == n:
                if len(notes_in_hit_zone) > 0:
                    notes_in_hit_zone[0].update(True)
                    recent_note_history.remove(notes_in_hit_zone[0])

                    score.hit()
                else:
                    # key was pressed but without any note
                    score.miss_click()

                break
                # exits the inner for
                # So, those ifs work as if-elif even inside the for loop

    # Move notes down
    all_notes_list.update(ticks)

    # If there are no more notes, end the game
    done = False
    if len(all_notes_list) == 0:
        game_is_running = False
        done = True
    return done


def step(action):
    global start_ms, update_ticks, done, ticks
    current_ms = pygame.time.get_ticks()
    delta_ms = current_ms - start_ms
    #delta_ms = clock.get_time()
    start_ms = current_ms
    # TODO: o jogo deve rodar baseado nos ticks e nao nos milissegundos
    #print("res:", song.resolution, "bpm: ", song.bpm, "ms/min:", MS_PER_MIN, "ts:",  song.ts)
    tick_per_ms = song.resolution * song.bpm / MS_PER_MIN
    delta_ticks = tick_per_ms * delta_ms
    update_ticks += delta_ticks
    num_updates = 0

    while (TICKS_PER_UPDATE <= update_ticks):
        # print('--------UPDATE-------')
        # print(ticks)
        # handle_inputs()
        done = update(score, ticks, action)
        update_ticks -= TICKS_PER_UPDATE
        num_updates += 1
        ticks += TICKS_PER_UPDATE

    render_interval = update_ticks / TICKS_PER_UPDATE
    render(screen, render_interval, score)
    rgb_array = pygame.surfarray.array3d(screen)

    clock.tick(60)

    reward = 0
    new_state = np.asarray(rgb_array, dtype=np.uint8)

    return reward, new_state, done


if __name__ == "__main__":

    args = arg_parser()

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    imgs = load_imgs()

    song, notes = load_chart(args.chart_file, imgs)

    all_notes_list = pygame.sprite.Group()
    buttons_sprites_list = pygame.sprite.Group()
    visible_notes_list = pygame.sprite.Group()

    Buttons = create_button_list(
        imgs, buttons_sprites_list)

    for note in notes:
        all_notes_list.add(note)
        # buttons_sprites_list.add(note)

    # Game Loop
    score = Score(decrease_mode=args.decrease_score)
    game_is_running = True
    clock = pygame.time.Clock()

    mixer.init()
    audio_name = '../charts/' + song.name
    print("You are playing {}.".format(audio_name))
    song_audio = mixer.Sound(audio_name)
    song_audio.set_volume(0.1)
    song_audio.play()

    ticks = 0
    update_ticks = 0 
    start_ms = pygame.time.get_ticks()
    done = False
    print("The Game is Running now!")

    while game_is_running:
        start_time = time.time()

        action = handle_inputs()
        # if action[0]:
        # print("Entering Step")
        step(action)
        # print("Leaving Step")

        # print(clock.get_time())
        # print(clock.get_rawtime())
        # print(clock.get_fps())
        # print('Game Speed: {}'.format((num_updates) / (time.time() - start_time)))
        # print('Render FPS: {}'.format(1.0 / (time.time() - start_time)))

    print("Pontuação Final: {} pontos!".format(score.value))

    song_audio.stop()
    mixer.quit()

    pygame.quit()
