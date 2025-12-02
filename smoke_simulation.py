import pygame
import random
import math

WIDTH, HEIGHT = 1000, 700
FPS = 60

BACKGROUND_COLOR = (30, 30, 30)
UI_BG_COLOR = (50, 50, 50)
SMOKE_COLOR = (200, 200, 200)
TEXT_COLOR = (255, 255, 255)
SLIDER_COLOR = (100, 100, 100)
KNOB_COLOR = (200, 200, 200)
OBSTACLE_COLOR = (100, 100, 150)

class SimulationParams:
    def __init__(self):
        self.gravity = 0.05
        self.buoyancy = 0.10
        self.wind = 0.0
        self.drag = 0.99
        self.particle_size = 4.0
        self.emission_rate = 1
        self.particle_lifetime = 1.6
        self.show_grid = False
        self.show_spatial_grid = False
        self.turbulence_strength = 0.5
        
        self.noise_scale = 0.005
        self.use_rk4 = True
        self.time = 0

        self.smoothing_radius = 30.0
        self.target_density = 1.0
        self.pressure_multiplier = 0.1
        self.interaction_radius = 30.0

params = SimulationParams()

class FixedGrid:
    def __init__(self, width, height, cell_size):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.cols = math.ceil(width / cell_size)
        self.rows = math.ceil(height / cell_size)
        self.cells = [[[] for _ in range(self.cols)] for _ in range(self.rows)]

    def clear(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.cells[r][c].clear()

    def insert(self, particle):
        cx = int(particle.x / self.cell_size)
        cy = int(particle.y / self.cell_size)
        
        if 0 <= cx < self.cols and 0 <= cy < self.rows:
            self.cells[cy][cx].append(particle)

    def query(self, x, y, radius):
        particles = []
        cx = int(x / self.cell_size)
        cy = int(y / self.cell_size)
        
        for r in range(cy - 1, cy + 2):
            for c in range(cx - 1, cx + 2):
                if 0 <= r < self.rows and 0 <= c < self.cols:
                    for p in self.cells[r][c]:
                        dx = p.x - x
                        dy = p.y - y
                        if dx*dx + dy*dy <= radius*radius:
                            particles.append(p)
        return particles

    def draw_grid(self, surface):
        for c in range(self.cols + 1):
            x = c * self.cell_size
            pygame.draw.line(surface, (50, 50, 50), (x, 0), (x, self.height))
        for r in range(self.rows + 1):
            y = r * self.cell_size
            pygame.draw.line(surface, (50, 50, 50), (0, y), (self.width, y))
        
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cells[r][c]:
                    rect = (c * self.cell_size, r * self.cell_size, self.cell_size, self.cell_size)
                    s = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
                    s.fill((0, 255, 0, 30))
                    surface.blit(s, rect)

class VectorGrid:
    def __init__(self, rows, cols, width, height):
        self.rows = rows
        self.cols = cols
        self.width = width
        self.height = height
        self.cell_w = width // cols
        self.cell_h = height // rows
        self.vectors = [[(0, 0) for _ in range(cols)] for _ in range(rows)]
    
    def get_potential(self, x, y, time):
        val = 0
        scale = params.noise_scale
        
        val += math.sin(x * scale + time) + math.cos(y * scale + time)
        val += 0.5 * (math.sin(x * scale * 2.0 + time * 1.5) + math.cos(y * scale * 2.0 + time * 1.5))
        val += 0.25 * (math.sin(x * scale * 4.0 + time * 2.0) + math.cos(y * scale * 4.0 + time * 2.0))
        
        return val

    def compute_curl(self, x, y, time):
        epsilon = 1.0 
        
        n_up = self.get_potential(x, y - epsilon, time)
        n_down = self.get_potential(x, y + epsilon, time)
        dy = (n_down - n_up) / (2 * epsilon)
        
        n_left = self.get_potential(x - epsilon, y, time)
        n_right = self.get_potential(x + epsilon, y, time)
        dx = (n_right - n_left) / (2 * epsilon)
        
        return dy, -dx

    def update(self, time):
        for r in range(self.rows):
            for c in range(self.cols):
                cx = c * self.cell_w + self.cell_w // 2
                cy = r * self.cell_h + self.cell_h // 2
                
                vx, vy = self.compute_curl(cx, cy, time)
                
                self.vectors[r][c] = (vx, vy)

    def get_force(self, x, y, time=None):
        if time is None: time = params.time
        return self.compute_curl(x, y, time)

    def draw(self, surface):
        for r in range(self.rows):
            for c in range(self.cols):
                cx = c * self.cell_w + self.cell_w // 2
                cy = r * self.cell_h + self.cell_h // 2
                vx, vy = self.vectors[r][c]
                
                vis_scale = 600.0
                end_x = cx + vx * vis_scale
                end_y = cy + vy * vis_scale
                
                color = (80, 80, 80)
                pygame.draw.line(surface, color, (cx, cy), (end_x, end_y), 1)
                pygame.draw.circle(surface, (100, 100, 100), (cx, cy), 2)

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
        pygame.draw.circle(surface, (200, 200, 250), (int(self.x), int(self.y)), self.radius, 2)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                dist = math.hypot(event.pos[0] - self.x, event.pos[1] - self.y)
                if dist < self.radius:
                    self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.x, self.y = event.pos

class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'ax', 'ay', 'life', 'decay', 'radius', 'growth', 'density', 'pressure')

    def __init__(self, x, y):
        self.reset(x, y)

    def apply_force(self, fx, fy):
        self.ax += fx
        self.ay += fy

    def compute_density_pressure(self, spatial_hash):
        self.density = 0.0
        neighbors = spatial_hash.query(self.x, self.y, params.smoothing_radius)
        
        for neighbor in neighbors:
            dx = self.x - neighbor.x
            dy = self.y - neighbor.y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist < params.smoothing_radius:
                q = 1.0 - (dist / params.smoothing_radius)
                self.density += q * q

        self.density = max(self.density, 0.0001)
        self.pressure = params.pressure_multiplier * max(0, self.density - params.target_density)

    def compute_pressure_force(self, spatial_hash):
        fx, fy = 0.0, 0.0
        neighbors = spatial_hash.query(self.x, self.y, params.smoothing_radius)
        
        sr_sq = params.smoothing_radius * params.smoothing_radius
        
        for neighbor in neighbors:
            if neighbor == self: continue
            
            dx = self.x - neighbor.x
            dy = self.y - neighbor.y
            dist_sq = dx*dx + dy*dy
            
            if 0 < dist_sq < sr_sq:
                dist = math.sqrt(dist_sq)
                q = 1.0 - (dist / params.smoothing_radius)
                
                press_term = (self.pressure + neighbor.pressure) / (2 * neighbor.density)
                force = -press_term * q
                
                fx += (dx / dist) * force
                fy += (dy / dist) * force
        
        max_force = 0.5
        force_sq = fx*fx + fy*fy
        if force_sq > max_force*max_force:
            force_mag = math.sqrt(force_sq)
            scale = max_force / force_mag
            fx *= scale
            fy *= scale
            
        self.apply_force(fx, fy)

    def update(self, obstacles, vector_grid):
        self.apply_force(0, params.gravity)
        self.apply_force(0, -params.buoyancy)

        wind_variation = random.uniform(-0.005, 0.005)
        self.apply_force(params.wind + wind_variation, 0)
        
        if params.turbulence_strength > 0:
            if params.use_rk4:
                dt = 1.0 
                dt_time = 0.01 
                
                k1x, k1y = vector_grid.get_force(self.x, self.y, params.time)
                
                k2x, k2y = vector_grid.get_force(
                    self.x + self.vx * 0.5 * dt, 
                    self.y + self.vy * 0.5 * dt, 
                    params.time + 0.5 * dt_time
                )
                
                k3x, k3y = vector_grid.get_force(
                    self.x + self.vx * 0.5 * dt, 
                    self.y + self.vy * 0.5 * dt, 
                    params.time + 0.5 * dt_time
                )
                
                k4x, k4y = vector_grid.get_force(
                    self.x + self.vx * dt, 
                    self.y + self.vy * dt, 
                    params.time + dt_time
                )
                
                avg_fx = (k1x + 2*k2x + 2*k3x + k4x) / 6.0
                avg_fy = (k1y + 2*k2y + 2*k3y + k4y) / 6.0
                
                self.apply_force(avg_fx * params.turbulence_strength, avg_fy * params.turbulence_strength)
                
            else:
                curl_x, curl_y = vector_grid.get_force(self.x, self.y, params.time)
                self.apply_force(curl_x * params.turbulence_strength, curl_y * params.turbulence_strength)
        
        self.vx += self.ax
        self.vy += self.ay
        self.vx *= params.drag
        self.vy *= params.drag
        
        next_x = self.x + self.vx
        next_y = self.y + self.vy

        for obs in obstacles:
            dx = next_x - obs.x
            dy = next_y - obs.y
            dist = math.hypot(dx, dy)
            
            min_dist = obs.radius + self.radius * 0.5 
            
            if dist < min_dist:
                nx = dx / dist
                ny = dy / dist
                
                overlap = min_dist - dist
                next_x += nx * overlap
                next_y += ny * overlap
                
                dot = self.vx * nx + self.vy * ny
                self.vx -= 2 * dot * nx
                self.vy -= 2 * dot * ny
                
                self.vx *= 0.5
                self.vy *= 0.5

        self.x = next_x
        self.y = next_y
        
        self.ax = 0
        self.ay = 0
        self.life -= self.decay
        self.radius += self.growth

    sprite_cache = {}

    def draw(self, surface):
        if self.life <= 0: return
        
        radius_int = int(self.radius)
        if radius_int < 1: return
        
        alpha = int(max(0, min(255, self.life)))
        if alpha < 5: return

        cache_key = (radius_int, alpha)
        if cache_key not in Particle.sprite_cache:
            temp_surface = pygame.Surface((radius_int * 2, radius_int * 2), pygame.SRCALPHA)
            color = (*SMOKE_COLOR, alpha)
            pygame.draw.circle(temp_surface, color, (radius_int, radius_int), radius_int)
            Particle.sprite_cache[cache_key] = temp_surface
        
        texture = Particle.sprite_cache[cache_key]
        surface.blit(texture, (int(self.x - radius_int), int(self.y - radius_int)))

    def reset(self, x, y):
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.5, 1.5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 1.0
        self.ax = 0
        self.ay = 0
        self.life = 255.0
        
        lifetime_frames = params.particle_lifetime * FPS
        base_decay = 255.0 / max(1, lifetime_frames)
        self.decay = random.uniform(base_decay * 0.8, base_decay * 1.2)
        
        self.radius = random.uniform(params.particle_size, params.particle_size * 1.5)
        self.growth = 0.05
        self.density = 0.0
        self.pressure = 0.0

    def is_dead(self):
        return self.life <= 0

class ParticlePool:
    def __init__(self, size):
        self.pool = [Particle(0, 0) for _ in range(size)]
        self.active_particles = []

    def get(self, x, y):
        if not self.pool:
            return None
        
        p = self.pool.pop()
        p.reset(x, y)
        self.active_particles.append(p)
        return p

    def return_particle(self, p):
        if p in self.active_particles:
            self.active_particles.remove(p)
            self.pool.append(p)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Smoke Physics Engine - Curl Noise")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 16)

    particle_pool = ParticlePool(200)
    particles = particle_pool.active_particles
    
    obstacles = [
        Obstacle(WIDTH // 2 + 150, HEIGHT // 2, 60),
        Obstacle(WIDTH // 2 + 250, HEIGHT // 2 - 100, 40)
    ]

    vector_grid = VectorGrid(20, 20, WIDTH, HEIGHT)
    spatial_hash = FixedGrid(WIDTH, HEIGHT, params.smoothing_radius)

    sliders = [
        Slider(50, 50, 200, 10, 1.0, 10.0, params.particle_size, "Initial Size"),
        Slider(50, 90, 200, 10, 0.0, 0.2, params.buoyancy, "Buoyancy Force"),
        Slider(50, 130, 200, 10, -0.1, 0.1, params.wind, "Wind Force"),
        Slider(50, 170, 200, 10, 0.90, 0.999, params.drag, "Air Resistance (Drag)"),
        
        Slider(50, 230, 200, 10, 0.0, 5.0, params.turbulence_strength, "Turbulence (Curl)"),
        Slider(50, 270, 200, 10, 0.001, 0.02, params.noise_scale, "Noise Scale (Zoom)"),
        
        Slider(50, 330, 200, 10, 10.0, 60.0, params.smoothing_radius, "Smoothing Radius"),
        Slider(50, 370, 200, 10, 0.1, 10.0, params.target_density, "Target Density"),
        Slider(50, 410, 200, 10, 0.0, 20.0, params.pressure_multiplier, "Pressure Strength")
    ]

    buttons = [
        ToggleButton(50, 460, 200, 30, "Show Vector Grid", lambda: params.show_grid, lambda x: setattr(params, 'show_grid', x)),
        ToggleButton(50, 500, 200, 30, "Show Spatial Grid", lambda: params.show_spatial_grid, lambda x: setattr(params, 'show_spatial_grid', x)),
        ToggleButton(50, 540, 200, 30, "Integrator: RK4", lambda: params.use_rk4, lambda x: setattr(params, 'use_rk4', x))
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
                if btn.text.startswith("Integrator"):
                    btn.text = f"Integrator: {'RK4' if params.use_rk4 else 'Euler'}"
                elif btn.text.startswith("Show Spatial"):
                    pass
            
            for obs in obstacles:
                obs.handle_event(event)
            
            if event.type == pygame.KEYDOWN:
                pass

        params.time += 0.01
        vector_grid.update(params.time)

        params.particle_size = sliders[0].val
        params.buoyancy = sliders[1].val
        params.wind = sliders[2].val
        params.drag = sliders[3].val
        
        params.turbulence_strength = sliders[4].val
        params.noise_scale = sliders[5].val
        
        params.smoothing_radius = sliders[6].val
        params.target_density = sliders[7].val
        params.pressure_multiplier = sliders[8].val
        
        if abs(spatial_hash.cell_size - params.smoothing_radius) > 1.0:
             spatial_hash = FixedGrid(WIDTH, HEIGHT, params.smoothing_radius)

        mouse_pos = pygame.mouse.get_pos()
        should_emit = False
        emit_pos = (WIDTH // 2 + 150, HEIGHT - 50)

        interacting_with_obstacle = any(obs.dragging for obs in obstacles)

        if pygame.mouse.get_pressed()[0] and not interacting_with_obstacle:
            if mouse_pos[0] > 300:
                should_emit = True
                emit_pos = mouse_pos
        else:
            should_emit = True
        
        if should_emit:
            for _ in range(params.emission_rate):
                px = emit_pos[0] + random.uniform(-10, 10)
                py = emit_pos[1] + random.uniform(-10, 10)
                p = particle_pool.get(px, py)
                if p:
                    p.vx += random.uniform(-0.5, 0.5)
                    p.vy += random.uniform(-0.5, 0.5)

        spatial_hash.clear()
        for p in particles:
            spatial_hash.insert(p)
            
        for p in particles:
            p.compute_density_pressure(spatial_hash)
            
        for p in particles:
            p.compute_pressure_force(spatial_hash)

        for i in range(len(particles) - 1, -1, -1):
            p = particles[i]
            p.update(obstacles, vector_grid)
            p.draw(screen)
            if p.is_dead():
                particle_pool.return_particle(p)

        for obs in obstacles:
            obs.draw(screen)

        if params.show_grid:
            vector_grid.draw(screen)
            
        if params.show_spatial_grid:
            spatial_hash.draw_grid(screen)

        for slider in sliders:
            slider.draw(screen, font)
            
        for btn in buttons:
            btn.draw(screen, font)
            
        info_text = font.render(f"Particles: {len(particles)} | FPS: {int(clock.get_fps())}", True, TEXT_COLOR)
        hint_text = font.render("Drag obstacles", True, TEXT_COLOR)
        screen.blit(info_text, (10, HEIGHT - 30))
        screen.blit(hint_text, (10, HEIGHT - 50))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
