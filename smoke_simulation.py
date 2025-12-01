import pygame
import random
import math

# Constants
WIDTH, HEIGHT = 1000, 700
FPS = 60

# Colors
BACKGROUND_COLOR = (30, 30, 30)
UI_BG_COLOR = (50, 50, 50)
SMOKE_COLOR = (200, 200, 200)
TEXT_COLOR = (255, 255, 255)
SLIDER_COLOR = (100, 100, 100)
KNOB_COLOR = (200, 200, 200)
OBSTACLE_COLOR = (100, 100, 150)

class SimulationParams:
    def __init__(self):
        self.gravity = 0.05   # Constant Gravity (Down)
        self.buoyancy = 0.10  # Buoyancy Force (Up)
        self.wind = 0.0
        self.drag = 0.99
        self.particle_size = 4.0
        self.emission_rate = 5
        self.life_decay = 2.0
        self.show_grid = False
        self.turbulence_strength = 0.5
        self.time = 0

params = SimulationParams()

class VectorGrid:
    def __init__(self, rows, cols, width, height):
        self.rows = rows
        self.cols = cols
        self.width = width
        self.height = height
        self.cell_w = width // cols
        self.cell_h = height // rows
        self.vectors = [[(0, 0) for _ in range(cols)] for _ in range(rows)]
    
    def update(self, time):
        # Generate a flow field using simple trig functions (pseudo-noise)
        scale = 0.1
        for r in range(self.rows):
            for c in range(self.cols):
                # Map grid position to noise space
                x = c * scale
                y = r * scale
                # Simple swirling pattern
                angle = math.sin(x + time * 0.5) + math.cos(y + time * 0.5) * 2.0
                # Add some variation
                angle += math.sin(y * 3.0 + time) * 0.5
                
                vx = math.cos(angle)
                vy = math.sin(angle)
                self.vectors[r][c] = (vx, vy)

    def get_force(self, x, y):
        c = int(x // self.cell_w)
        r = int(y // self.cell_h)
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.vectors[r][c]
        return (0, 0)

    def draw(self, surface):
        for r in range(self.rows):
            for c in range(self.cols):
                cx = c * self.cell_w + self.cell_w // 2
                cy = r * self.cell_h + self.cell_h // 2
                vx, vy = self.vectors[r][c]
                
                # Draw arrow
                end_x = cx + vx * 10
                end_y = cy + vy * 10
                color = (60, 60, 60)
                pygame.draw.line(surface, color, (cx, cy), (end_x, end_y), 1)
                pygame.draw.circle(surface, color, (int(end_x), int(end_y)), 2)

class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, initial_val, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.label = label
        self.dragging = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self.update_val(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.update_val(event.pos[0])

    def update_val(self, mouse_x):
        ratio = (mouse_x - self.rect.x) / self.rect.width
        ratio = max(0, min(1, ratio))
        self.val = self.min_val + (self.max_val - self.min_val) * ratio

    def draw(self, surface, font):
        label_surf = font.render(f"{self.label}: {self.val:.3f}", True, TEXT_COLOR)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 25))
        pygame.draw.rect(surface, SLIDER_COLOR, self.rect)
        ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        knob_x = self.rect.x + self.rect.width * ratio
        pygame.draw.circle(surface, KNOB_COLOR, (int(knob_x), self.rect.centery), 10)

class Button:
    def __init__(self, x, y, w, h, text, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.hovered and event.button == 1:
                self.callback()

    def draw(self, surface, font):
        color = (100, 100, 100) if not self.hovered else (150, 150, 150)
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2)
        
        text_surf = font.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

class ToggleButton(Button):
    def __init__(self, x, y, w, h, text, getter, setter):
        super().__init__(x, y, w, h, text, None)
        self.getter = getter
        self.setter = setter

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.hovered and event.button == 1:
                self.setter(not self.getter())

    def draw(self, surface, font):
        is_active = self.getter()
        color = (100, 150, 100) if is_active else (100, 50, 50)
        if self.hovered:
            color = (min(255, color[0]+30), min(255, color[1]+30), min(255, color[2]+30))
            
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2)
        
        status = "ON" if is_active else "OFF"
        text_surf = font.render(f"{self.text}: {status}", True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

class Obstacle:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.dragging = False

    def draw(self, surface):
        pygame.draw.circle(surface, OBSTACLE_COLOR, (int(self.x), int(self.y)), self.radius)
        # Draw border
        pygame.draw.circle(surface, (200, 200, 250), (int(self.x), int(self.y)), self.radius, 2)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                dist = math.hypot(event.pos[0] - self.x, event.pos[1] - self.y)
                if dist < self.radius:
                    self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.x, self.y = event.pos

class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.5, 1.5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 1.0
        self.ax = 0
        self.ay = 0
        self.life = 255.0
        self.decay = random.uniform(params.life_decay * 0.8, params.life_decay * 1.2)
        self.radius = random.uniform(params.particle_size, params.particle_size * 1.5)
        self.growth = 0.05

    def apply_force(self, fx, fy):
        self.ax += fx
        self.ay += fy

    def update(self, obstacles, vector_grid):
        # 1. Gravity (Down)
        self.apply_force(0, params.gravity)
        
        # 2. Buoyancy (Up)
        self.apply_force(0, -params.buoyancy)

        # 3. Wind / Vector Field
        # Global wind
        wind_variation = random.uniform(-0.005, 0.005)
        self.apply_force(params.wind + wind_variation, 0)
        
        # Grid Turbulence
        if params.turbulence_strength > 0:
            grid_fx, grid_fy = vector_grid.get_force(self.x, self.y)
            self.apply_force(grid_fx * params.turbulence_strength * 0.1, grid_fy * params.turbulence_strength * 0.1)
        
        self.vx += self.ax
        self.vy += self.ay
        self.vx *= params.drag
        self.vy *= params.drag
        
        # Proposed new position
        next_x = self.x + self.vx
        next_y = self.y + self.vy

        # Collision Detection & Response with Obstacles
        for obs in obstacles:
            dx = next_x - obs.x
            dy = next_y - obs.y
            dist = math.hypot(dx, dy)
            
            # Simple collision check
            min_dist = obs.radius + self.radius * 0.5 
            
            if dist < min_dist:
                # Collision detected!
                # Calculate normal vector
                nx = dx / dist
                ny = dy / dist
                
                # Push particle out
                overlap = min_dist - dist
                next_x += nx * overlap
                next_y += ny * overlap
                
                # Reflect velocity (Bounce)
                # v_new = v - 2 * (v . n) * n
                dot = self.vx * nx + self.vy * ny
                self.vx -= 2 * dot * nx
                self.vy -= 2 * dot * ny
                
                # Dampen the bounce
                self.vx *= 0.5
                self.vy *= 0.5

        self.x = next_x
        self.y = next_y
        
        self.ax = 0
        self.ay = 0
        self.life -= self.decay
        self.radius += self.growth

    def draw(self, surface):
        if self.life > 0 and self.life < 5: return
        radius_int = int(self.radius)
        if radius_int < 1: return

        temp_surface = pygame.Surface((radius_int * 2, radius_int * 2), pygame.SRCALPHA)
        alpha = int(max(0, min(255, self.life)))
        
        temp_surface = pygame.Surface((radius_int * 2, radius_int * 2), pygame.SRCALPHA)
        alpha = int(max(0, min(255, self.life)))
        color = (*SMOKE_COLOR, alpha)

        pygame.draw.circle(temp_surface, color, (radius_int, radius_int), radius_int)
        surface.blit(temp_surface, (int(self.x - radius_int), int(self.y - radius_int)))

    def is_dead(self):
        return self.life <= 0

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Smoke Physics Engine")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 16)

    particles = []
    
    # Obstacles Setup
    obstacles = [
        Obstacle(WIDTH // 2 + 150, HEIGHT // 2, 60),
        Obstacle(WIDTH // 2 + 250, HEIGHT // 2 - 100, 40)
    ]

    # Vector Grid
    vector_grid = VectorGrid(20, 20, WIDTH, HEIGHT)

    sliders = [
        Slider(50, 50, 200, 10, 0.0, 0.2, params.buoyancy, "Buoyancy Force"),
        Slider(50, 100, 200, 10, -0.1, 0.1, params.wind, "Wind Force"),
        Slider(50, 150, 200, 10, 0.90, 0.999, params.drag, "Air Resistance (Drag)"),
        Slider(50, 200, 200, 10, 1.0, 10.0, params.particle_size, "Initial Size"),
        Slider(50, 250, 200, 10, 1, 20, params.emission_rate, "Emission Rate"),
        Slider(50, 300, 200, 10, 0.5, 5.0, params.life_decay, "Decay Rate (Life)"),
        Slider(50, 350, 200, 10, 0.0, 2.0, params.turbulence_strength, "Turbulence (Grid)")
    ]

    buttons = [
        ToggleButton(50, 400, 200, 40, "Show Grid", lambda: params.show_grid, lambda x: setattr(params, 'show_grid', x))
    ]

    running = True
    while running:
        clock.tick(FPS)
        screen.fill(BACKGROUND_COLOR)
        pygame.draw.rect(screen, UI_BG_COLOR, (0, 0, 300, HEIGHT))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            for slider in sliders:
                slider.handle_event(event)
            
            for btn in buttons:
                btn.handle_event(event)
            
            for obs in obstacles:
                obs.handle_event(event)
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    params.show_grid = not params.show_grid

        params.time += 0.01
        vector_grid.update(params.time)

        params.buoyancy = sliders[0].val
        params.wind = sliders[1].val
        params.drag = sliders[2].val
        params.particle_size = sliders[3].val
        params.emission_rate = int(sliders[4].val)
        params.life_decay = sliders[5].val
        params.turbulence_strength = sliders[6].val

        # Emitter
        mouse_pos = pygame.mouse.get_pos()
        should_emit = False
        emit_pos = (WIDTH // 2 + 150, HEIGHT - 50)

        # Check if mouse is interacting with obstacles
        interacting_with_obstacle = any(obs.dragging for obs in obstacles)

        if pygame.mouse.get_pressed()[0] and not interacting_with_obstacle:
            if mouse_pos[0] > 300:
                should_emit = True
                emit_pos = mouse_pos
        else:
            should_emit = True
        
        if should_emit:
            for _ in range(params.emission_rate):
                particles.append(Particle(emit_pos[0], emit_pos[1]))

        # Update Particles
        for i in range(len(particles) - 1, -1, -1):
            p = particles[i]
            p.update(obstacles, vector_grid) # Pass obstacles and grid
            p.draw(screen)
            if p.is_dead():
                particles.pop(i)

        # Draw Obstacles
        for obs in obstacles:
            obs.draw(screen)

        # Draw GUI
        if params.show_grid:
            vector_grid.draw(screen)

        for slider in sliders:
            slider.draw(screen, font)
            
        for btn in buttons:
            btn.draw(screen, font)
            
        info_text = font.render(f"Particles: {len(particles)} | FPS: {int(clock.get_fps())}", True, TEXT_COLOR)
        hint_text = font.render("Drag obstacles | Press 'G' to toggle Grid", True, TEXT_COLOR)
        screen.blit(info_text, (10, HEIGHT - 30))
        screen.blit(hint_text, (10, HEIGHT - 50))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
