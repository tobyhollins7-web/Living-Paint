# main.py
# connects everything and runs the application
import pygame
from vector2 import Vector2
from simulation import update_particles
from renderer import render_particles, render_radius_indicator, render_grid
from brushes import create_particle
from attractors import Attractor
from species import Species
from spatial_grid import SpatialGrid

# General config
WIDTH, HEIGHT = 800, 600
BACKGROUND_COLOR = (20, 20, 30)
FPS = 240
GRID_OVERLAY_COLOUR = (55, 55, 75)

# INDICATOR GENERAL SETUP
INDICATOR_LINEWIDTH = 5

# Particle spawning parameters (Left click)
PARTICLE_SPAWN_RATE = 40  # Particles/second
BRUSH_RADIUS = 40

# Attraction Parameters (Right click)
ATTRACTION_STRENGTH = 5000
ATTRACTION_RADIUS = 100
ATTRACTION_INDICATOR_COLOUR = (130, 120, 255)

# Global species parameters
SPECIES_INTERACTION_RADIUS = 100.0

# Physics values
DRAG_COEFFICIENT = 0.5
PAIR_DAMPING_COEFFICIENT = 5.0
REPULSION_COEFFICIENT = 500.0

# Species definitions
green_species = Species(
    id=0,
    name="Green",
    colour=(80, 220, 120),
    radius=10.0,
    interaction_strengths={
        0: 100.0,  # Green clusters with green
        1: -300.0,  # Green flees red
    },
)

red_species = Species(
    id=1,
    name="Red",
    colour=(230, 90, 100),
    radius=7.0,
    interaction_strengths={
        0: 40.0,  # Red pursues green
        1: -10.0,  # Red spreads away from red
    },
)

MAXIMUM_CONTACT_DISTANCE = 2.0 * max(green_species.radius, red_species.radius)
GRID_CELL_SIZE = max(SPECIES_INTERACTION_RADIUS, MAXIMUM_CONTACT_DISTANCE)

spatial_grid = SpatialGrid(domain_width=WIDTH, domain_height=HEIGHT, cell_size=GRID_CELL_SIZE)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Living Paint")

particles = []

spawn_interval = 1.0 / PARTICLE_SPAWN_RATE  # Interval of time taken between particle spawns in seconds

clock = pygame.time.Clock()
running = True

spawn_timer = 0.0
selected_species = green_species
grid_overlay = False

while running:
    attractor = None
    dt = clock.tick(FPS) / 1000.0  # time elapsed per frame in seconds

    for event in pygame.event.get():
        # In the event of clicking off the display
        if event.type == pygame.QUIT:
            running = False

        # Keyboard press event
        elif event.type == pygame.KEYDOWN:
            # Key 1 press - Green Species
            if event.key == pygame.K_1:
                selected_species = green_species
                print(f"{selected_species.name} species selected")
            # Key 2 press - Red species
            elif event.key == pygame.K_2:
                selected_species = red_species
                print(f"{selected_species.name} species selected")

            elif event.key == pygame.K_g:
                grid_overlay = not grid_overlay
                if grid_overlay:
                    print("Grid overlay enabled")
                else:
                    print("Grid overlay disabled")

    # Get mouse position
    mouse_position = pygame.mouse.get_pos()
    cursor_position = Vector2(mouse_position[0], mouse_position[1])

    # Check to see if left/right mouse buttons are being held down
    mouse_buttons = pygame.mouse.get_pressed()
    left_mouse_held = mouse_buttons[0]
    right_mouse_held = mouse_buttons[2]

    # Case where left mouse button is held down
    if left_mouse_held:
        spawn_timer += dt

        # If left mouse and spawn timer is applicable, then spawn a particle
        while spawn_timer >= spawn_interval:
            new_particle = create_particle(BRUSH_RADIUS, selected_species, cursor_position, WIDTH, HEIGHT)
            particles.append(new_particle)
            spawn_timer -= spawn_interval

    else:
        spawn_timer = 0.0

    if right_mouse_held:
        attractor = Attractor(
            position=cursor_position,
            strength=ATTRACTION_STRENGTH,
            radius=ATTRACTION_RADIUS,
        )

    # Advance the simulation
    update_particles(particles, dt, WIDTH, HEIGHT, attractor, DRAG_COEFFICIENT, REPULSION_COEFFICIENT,
                     SPECIES_INTERACTION_RADIUS, PAIR_DAMPING_COEFFICIENT, spatial_grid)

    # Clear the previous frame
    screen.fill(BACKGROUND_COLOR)

    if grid_overlay:
        render_grid(screen, spatial_grid, GRID_OVERLAY_COLOUR)

    # Render particles
    render_particles(screen, particles)

    # Render active tool indicators
    if left_mouse_held:
        render_radius_indicator(
            screen,
            cursor_position,
            BRUSH_RADIUS,
            selected_species.colour,
            INDICATOR_LINEWIDTH,
        )

    if right_mouse_held:
        render_radius_indicator(
            screen,
            cursor_position,
            ATTRACTION_RADIUS,
            ATTRACTION_INDICATOR_COLOUR,
            INDICATOR_LINEWIDTH,
        )

    # Display the completed frame
    pygame.display.flip()

# Quit the application
pygame.quit()