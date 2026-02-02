from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.prefabs.health_bar import HealthBar 
from PIL import Image
import random
import math
import os
from ursina import *

app = Ursina(
    title='HELLGRID: THE TRUE ARENA',
    icon='assets/icon256.ico',
    borderless=False,
    fullscreen=False,
    editor_ui_enabled=False
)

def final_fix():
    window.title = 'HELLGRID: THE TRUE ARENA'
    print(f"Aktualny tytuł w pamięci: {window.title}")

invoke(final_fix, delay=1.0)


# --- 1. TEKSTURY ---
def create_tex(color_base, var=0.1):
    img = Image.new('RGB', (64, 64), color_base)
    pix = img.load()
    for x in range(64):
        for y in range(64):
            n = random.uniform(-var, var) * 255
            pix[x,y] = tuple(min(255, max(0, int(c + n))) for c in color_base)
    return Texture(img)

tex_floor = create_tex((10, 10, 10))
tex_wall = create_tex((80, 5, 5), var=0.3)
tex_pillar = create_tex((30, 30, 30), var=0.2)

# --- 2. DANE GRY ---
game_data = {
    'wave': 0, 'ammo': 50, 'dmg_mult': 1.0, 'vamp': 0,
    'is_leveling': False, 'next_fire': 0, 'fire_rate': 0.22
}

# --- 3. KLASY ---

class Player(FirstPersonController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.health = 100
        self.speed = 17
        self.jump_height = 3.5
        
        # UI
        self.hp_bar = HealthBar(bar_color=color.red, position=(-0.85, -0.45), scale=(0.4, 0.02))
        self.stats = Text(text='', position=(-0.88, 0.46), scale=1.1, color=color.white)
        self.crosshair = Text(text='+', origin=(0,0), scale=2, color=color.red)
        
        # Modele Broni
        self.gun = Entity(parent=camera, model='cube', color=color.gray, scale=(0.12, 0.12, 0.8), position=(0.5, -0.4, 0.8))
        self.knife = Entity(parent=camera, model='cube', color=color.light_gray, scale=(0.04, 0.15, 0.6), position=(0.5, -0.4, 0.6), visible=False, rotation=(90,0,0))
        self.update_ui()

    def update_ui(self):
        self.hp_bar.value = self.health
        self.stats.text = f"WAVE: {game_data['wave']} | AMMO: {game_data['ammo']} | DMG: x{game_data['dmg_mult']:.1f}\nHP: {int(self.health)}"

    def damage_indicator(self):
        # Tworzymy obiekt, który domyślnie jest niewidoczny (alpha=0)
        inf = Entity(
            parent=camera.ui, 
            model='quad', 
            scale=100, 
            color=color.rgba(255, 0, 0, 0),
            add_to_scene_base=False
        )
        # Błyskawicznie pokazujemy go na 5% i każemy mu zniknąć
        inf.alpha = 0.05
        inf.fade_out(duration=0.2) 
        destroy(inf, delay=0.25)

    def input(self, key):
            super().input(key)
            
                # Ratunkowy teleport na środek mapy (klawisz R)
            if key == 'r':
                self.position = Vec3(0, 2, 0)
                self.rotation = Vec3(0, 0, 0)
                Audio('assets/sound/teleport', volume=0.4) 
                print("System: Gracz zresetowany na środek mapy.")

            # Dźwięk skoku
            if key == 'space':
                Audio('assets/sound/jump', volume=0.5)

            # Dźwięk Dasha
            if key == 'shift':
                Audio('assets\sound\dash.wav', volume=0.6)
                self.speed = 45
                invoke(setattr, self, 'speed', 17, delay=0.15)
                
            if key == '1': self.gun.visible, self.knife.visible = True, False
            if key == '2': self.gun.visible, self.knife.visible = False, True
            if key == 'left mouse down' and self.enabled: self.attack()

    def attack(self):
        if time.time() < game_data['next_fire']: return
        
        if self.gun.visible and game_data['ammo'] > 0:
            Audio('assets/sound/shoot.wav', volume=0.4)
            game_data['ammo'] -= 1
            game_data['next_fire'] = time.time() + game_data['fire_rate']
            self.gun.blink(color.white, duration=0.05)
            camera.shake(duration=0.1, magnitude=0.05)
            
            hit = raycast(camera.world_position, camera.forward, distance=100, ignore=(self,))
            if hit.hit and hasattr(hit.entity, 'take_damage'):
                hit.entity.take_damage(38 * game_data['dmg_mult'], self.world_position, power=1.5)
                self.health = min(100, self.health + game_data['vamp'])
            self.update_ui()
            
        elif self.knife.visible:
            Audio('assets/sound/knife', volume=0.1)
            game_data['next_fire'] = time.time() + 0.4
            self.knife.animate_position((0.5, -0.2, 1.3), duration=0.1)
            invoke(setattr, self.knife, 'position', (0.5, -0.4, 0.6), delay=0.15)
            hit = raycast(camera.world_position, camera.forward, distance=4, ignore=(self,))
            if hit.hit and hasattr(hit.entity, 'take_damage'):
                # Nóż odrzuca
                hit.entity.take_damage(55 * game_data['dmg_mult'], self.world_position, power=4.0)
                self.health = min(100, self.health + game_data['vamp'] * 2)
            self.update_ui()

    def take_damage(self, amt):
        self.health -= amt
        self.update_ui()
        self.damage_indicator()
        camera.shake(duration=0.1, magnitude=0.1)
        if self.health <= 0:
            self.enabled = False; mouse.locked = False
            Text("YOU DIED IN THE GRID", origin=(0,0), scale=4, color=color.red, background=True)

class Enemy(Entity):
    def __init__(self, target, etype="std", **kwargs):
        super().__init__(model='cube', collider='box', **kwargs)
        self.target = target
        
        wave_mod = 1.0 + (game_data['wave'] * 0.12)
        cfg = {
            "std":  {'hp':65 * wave_mod, 'spd':7.5, 'dmg':4, 'col':color.red, 's':(1,1.5,1)},
            "fast": {'hp':35 * wave_mod, 'spd':13, 'dmg':3, 'col':color.yellow, 's':(0.8,1,0.8)},
            "tank": {'hp':600 * wave_mod, 'spd':4.5, 'dmg':12, 'col':color.magenta, 's':(2.2,2.8,2.2)},
            "boss": {'hp':5000 * wave_mod, 'spd':3.8, 'dmg':25, 'col':color.orange, 's':(6,10,6)}
        }[etype]
        
        self.health = cfg['hp']
        self.speed = cfg['spd']
        self.damage = cfg['dmg']
        self.color = cfg['col']
        self.scale = cfg['s']

    def update(self):
        if not self.target.enabled or game_data['is_leveling']: return
        
        dist = distance_xz(self.position, self.target.position)
        
        # Kolizja wrogow
        sep = Vec3(0,0,0)
        for e in [e for e in scene.entities if isinstance(e, Enemy) and e != self]:
            if distance_xz(self.position, e.position) < 2.0:
                sep += (self.position - e.position).normalized() * 3
        
        move_dir = ((self.target.position - self.position).normalized() + sep).normalized()
        move_dir.y = 0 # WYMUSZENIE RUCHU TYLKO PO ZIEMI
        
        if dist > 1.2:
            self.position += move_dir * self.speed * time.dt
            self.look_at_2d(self.target)
        
        if dist < 2.0:
            self.target.take_damage(self.damage * time.dt)

    def take_damage(self, amt, origin, power):
        self.health -= amt
        self.blink(color.white, duration=0.1)
        
        knock_dir = (self.world_position - origin).normalized()
        knock_dir.y = 0 # Blokuje przeciwnika na ziemi
        self.position += knock_dir * power
        
        # resetuje Y do poziomu podlogi
        self.y = self.scale_y / 2 

        if self.health <= 0:
            Audio('assets/sound/enemy_death.wav', volume=0.2)
            if random.random() < 0.25:
                a = Entity(model='cube', color=color.yellow, scale=0.3, position=self.position + Vec3(0,0.5,0))
                def collect():
                    if distance(a, player) < 1.6: 
                        game_data['ammo'] += 20; player.update_ui(); destroy(a)
                a.update = collect
            destroy(self)

# --- 4. LEVEL UP ---
class LevelMenu(Entity):
    def __init__(self):
        super().__init__(parent=camera.ui, model='quad', scale=(0.7, 0.5), color=color.black90, enabled=False)
        self.title = Text("LEVEL UP", parent=self, y=0.4, scale=2, origin=(0,0), color=color.red)
        self.btns = [Button(parent=self, x=(i-1)*0.25, y=-0.1, scale=(0.2, 0.3), color=color.dark_gray) for i in range(3)]

    def show(self):
        game_data['is_leveling'] = True
        self.enabled = True; player.enabled, mouse.locked = False, False
        pool = [
            ("RESTORE", "Full HP", self.h), ("SUPPLY", "+150 Ammo", self.a),
            ("POWER", "+0.2x Dmg", self.d), ("VAMP", "+1 Vamp", self.v)
        ]
        opts = random.sample(pool, 3)
        for i, o in enumerate(opts):
            self.btns[i].text = f"{o[0]}\n\n{o[1]}"
            self.btns[i].on_click = o[2]

    def close(self):
        self.enabled = False; player.enabled, mouse.locked = True, True; game_data['is_leveling'] = False; spawn_wave()
        player.cursor.enabled = False
    def h(self): player.health = 100; self.close()
    def a(self): game_data['ammo'] += 150; self.close()
    def d(self): game_data['dmg_mult'] += 0.2; self.close()
    def v(self): game_data['vamp'] += 1; self.close()

lvl_menu = LevelMenu()

# --- 5. ŚWIAT ---
def build_arena():
    Entity(model='plane', scale=80, texture=tex_floor, texture_scale=(16,16), collider='box')
    for i in range(4):
        w = Entity(model='cube', texture=tex_wall, collider='box', scale=(80, 20, 1))
        w.rotation_y = i * 90; w.position = w.forward * 40 + Vec3(0, 10, 0)
    for _ in range(12):
        Entity(model='cube', texture=tex_pillar, collider='box', scale=(random.randint(2,4), 10, 2), 
               position=(random.uniform(-30,30), 5, random.uniform(-30,30)))

player = Player(position=(0,1,0))
player.cursor.enabled = False  # Usuwa domyślnyc celownik

def spawn_wave():
    game_data['wave'] += 1
    count = 5 + int(game_data['wave'] * 1.5)
    if game_data['wave'] % 10 == 0:
        Enemy(player, etype="boss", position=(0, 5, 35))
    else:
        for _ in range(count):
            dist, ang = random.uniform(25, 38), random.uniform(0, 360)
            et = random.choice(["std", "fast", "tank"]) if game_data['wave'] > 3 else "std"
            Enemy(player, etype=et, position=(dist*math.cos(ang), 1, dist*math.sin(ang)))

def update():
    if not player.enabled or game_data['is_leveling']: return
    enemies = [e for e in scene.entities if isinstance(e, Enemy)]
    if not enemies:
        if game_data['wave'] > 0 and game_data['wave'] % 2 == 0: lvl_menu.show()
        else: spawn_wave()



# --- 6. URUCHOMIENIE GRY ---
build_arena()

# Muzyka
bg_music = Audio('assets/sound/ambient_hell', loop=True, volume=0.1)
# Ladowanie narzedzia do debugowania
try:
    from debug_tool import DebugTool
    debug = DebugTool(player, game_data, spawn_wave, lvl_menu)
    print("System: Debug Tool aktywny.")
except ImportError:
    print("System: Tryb gracza (brak narzędzi debugowania).")

app.run()
