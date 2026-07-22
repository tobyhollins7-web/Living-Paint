# main.py
# connects everything and runs the application
import pygame
from vector2 import Vector2
from simulation import update_particles
from renderer import render_particles, render_radius_indicator, render_grid
from brushes import create_brush_particle
from attractors import Attractor
from species import Species, FeedingRule, ReproductionRule
from spatial_grid import SpatialGrid

# General config
WIDTH, HEIGHT = 800, 600
BACKGROUND_COLOR = (20, 20, 30)
FPS = 120
GRID_OVERLAY_COLOUR = (55, 55, 75)

# INDICATOR GENERAL SETUP
INDICATOR_LINEWIDTH = 5

# Particle spawning parameters (Left click)
PARTICLE_SPAWN_RATE = 40  # Particles/second
BRUSH_RADIUS = 40

# Attraction Parameters (Right click)
ATTRACTION_STRENGTH = 5000
ATTRACTION_RADIUS = 50
ATTRACTION_INDICATOR_COLOUR = (130, 120, 255)

# Global species parameters
SPECIES_INTERACTION_RADIUS = 100.0
MAXIMUM_PARTICLES = 1000

# Physics values
DRAG_COEFFICIENT = 0.5
PAIR_DAMPING_COEFFICIENT = 3.0
REPULSION_COEFFICIENT = 1200.0
PHYSICS_TIMESTEP = 1.0 / 120.0
MAX_PHYSICS_STEPS = 4

# Species definitions
green_species = Species(
    id=0,
    name="Green",
    colour=(80, 220, 120),
    radius=15.0,

    starting_energy=10.0,
    maximum_energy = 20.0,
    metabolism=1.0,

    energy_generation=1.5,

    reproduction_rule=ReproductionRule(
        reproduction_threshold=11.0,
        reproduction_cost=3.0,
        offspring_energy=2.0,
        reproduction_cooldown=1.0,
    ),

    interaction_strengths={
        0: 300.0,
        1: -500.0,
    },
    feeding_rules={},
)

red_species = Species(
    id=1,
    name="Red",
    colour=(230, 90, 100),
    radius=20.0,

    starting_energy=30.0,
    maximum_energy=50.0,
    metabolism=3.0,

    reproduction_rule=ReproductionRule(
        reproduction_threshold=45.0,
        reproduction_cost=20.0,
        offspring_energy=15.0,
        reproduction_cooldown=5.0,
    ),

    energy_generation=0.0,

    interaction_strengths={
        0: 800.0,
        1: -100.0,
    },
    feeding_rules={
        0: FeedingRule(
            rate=10.0,
            efficiency=0.75,
        ),
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
physics_accumulator = 0.0

while running:
    attractor = None
    frame_dt = min(clock.tick(FPS) / 1000.0, MAX_PHYSICS_STEPS * PHYSICS_TIMESTEP)  # time elapsed per frame in seconds
    physics_accumulator += frame_dt

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
        spawn_timer += frame_dt

        # If left mouse and spawn timer is applicable, then spawn a particle
        while spawn_timer >= spawn_interval:
            new_particle = create_brush_particle(BRUSH_RADIUS, selected_species, cursor_position, WIDTH, HEIGHT)
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
    physics_steps = 0

    while physics_accumulator >= PHYSICS_TIMESTEP and physics_steps < MAX_PHYSICS_STEPS:
        particles = update_particles(
            particles=particles,
            dt=PHYSICS_TIMESTEP,
            width=WIDTH,
            height=HEIGHT,
            attractor=attractor,
            drag_coefficient=DRAG_COEFFICIENT,
            repulsion_coefficient=REPULSION_COEFFICIENT,
            species_interaction_radius=SPECIES_INTERACTION_RADIUS,
            maximum_particles=MAXIMUM_PARTICLES,
            pair_damping_coefficient=PAIR_DAMPING_COEFFICIENT,
            spatial_grid=spatial_grid,
        )
        physics_accumulator -= PHYSICS_TIMESTEP
        physics_steps += 1

    # Clear the previous frame
    screen.fill(BACKGROUND_COLOR)

    if grid_overlay:
        render_grid(screen, spatial_grid, GRID_OVERLAY_COLOUR)

    # Render particles
    render_particles(screen, particles, BACKGROUND_COLOR)

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

    green_count = sum(
        particle.species.id == green_species.id
        for particle in particles
    )

    red_count = sum(
        particle.species.id == red_species.id
        for particle in particles
    )

    pygame.display.set_caption(
        f"Living Paint | Green: {green_count} | "
        f"Red: {red_count} | Total: {len(particles)}"
    )

    # Display the completed frame
    pygame.display.flip()

# Quit the application
pygame.quit()