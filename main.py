# main.py
# connects everything and runs the application
import pygame
from vector2 import Vector2
from simulation import update_particles
from renderer import render_particles, render_radius_indicator, render_grid, render_density_field, render_density_grid_overlay
from brushes import create_brush_particle
from attractors import Attractor
from species import Species, FeedingRule, ReproductionRule
from spatial_grid import SpatialGrid
from density_field import DensityField

# General config
WIDTH, HEIGHT = 800, 600
BACKGROUND_COLOR = (20, 20, 30)
FPS = 60
GRID_OVERLAY_COLOUR = (55, 55, 75)

# Density Field
DENSITY_CELL_SIZE = 4.0
DENSITY_INFLUENCE_RADIUS = 25.0
DENSITY_GAIN = 2.0
DENSITY_GRID_COLOUR = (0, 0, 255)

# INDICATOR GENERAL SETUP
INDICATOR_LINEWIDTH = 5

# Particle spawning parameters (Left click)
PARTICLE_SPAWN_RATE = 300  # Particles/second
BRUSH_RADIUS = 40

# Attraction Parameters (Right click)
ATTRACTION_STRENGTH = 5000
ATTRACTION_RADIUS = 20
ATTRACTION_INDICATOR_COLOUR = (130, 120, 255)

# Global species parameters
SPECIES_INTERACTION_RADIUS = 15.0
MAXIMUM_PARTICLES = 10000

# Physics values
DRAG_COEFFICIENT = 2.5
PAIR_DAMPING_COEFFICIENT = 6.0
REPULSION_COEFFICIENT = 800.0
PHYSICS_TIMESTEP = 1.0 / 60.0
MAX_PHYSICS_STEPS = 4

# Species definitions
# Cyan hunts Gold and is hunted by Coral
cyan_species = Species(
    id=0,
    name="Cyan",
    colour=(45, 225, 210),
    radius=5.0,

    starting_energy=18.0,
    maximum_energy=32.0,
    metabolism=1.1,
    energy_generation=0.55,

    reproduction_rule=ReproductionRule(
        reproduction_threshold=25.0,
        reproduction_cost=8.0,
        offspring_energy=7.0,
        reproduction_cooldown=3.0,
    ),

    interaction_strengths={
        0: 180.0,    # Forms loose cyan colonies
        1: -700.0,   # Flees Coral
        2: -80.0,    # Slightly avoids Violet
        3: 850.0,    # Hunts Gold
    },

    feeding_rules={
        3: FeedingRule(
            rate=7.0,
            efficiency=0.70,
        ),
    },
)

# Coral hunts Cyan and is hunted by Violet
coral_species = Species(
    id=1,
    name="Coral",
    colour=(255, 80, 135),
    radius=5.5,

    starting_energy=19.0,
    maximum_energy=34.0,
    metabolism=1.2,
    energy_generation=0.5,

    reproduction_rule=ReproductionRule(
        reproduction_threshold=27.0,
        reproduction_cost=9.0,
        offspring_energy=7.5,
        reproduction_cooldown=3.5,
    ),

    interaction_strengths={
        0: 900.0,    # Hunts Cyan
        1: 120.0,    # Forms loose packs
        2: -750.0,   # Flees Violet
        3: -100.0,   # Slightly avoids Gold
    },

    feeding_rules={
        0: FeedingRule(
            rate=7.5,
            efficiency=0.72,
        ),
    },
)


# Violet hunts Coral and is hunted by Gold
violet_species = Species(
    id=2,
    name="Violet",
    colour=(150, 90, 255),
    radius=6.0,

    starting_energy=20.0,
    maximum_energy=36.0,
    metabolism=1.3,
    energy_generation=0.45,

    reproduction_rule=ReproductionRule(
        reproduction_threshold=29.0,
        reproduction_cost=10.0,
        offspring_energy=8.0,
        reproduction_cooldown=4.0,
    ),

    interaction_strengths={
        0: -100.0,   # Slightly avoids Cyan
        1: 950.0,    # Hunts Coral
        2: 80.0,     # Weak group attraction
        3: -800.0,   # Flees Gold
    },

    feeding_rules={
        1: FeedingRule(
            rate=8.0,
            efficiency=0.74,
        ),
    },
)


# Gold hunts Violet and is hunted by Cyan
gold_species = Species(
    id=3,
    name="Gold",
    colour=(255, 190, 55),
    radius=4.5,

    starting_energy=17.0,
    maximum_energy=30.0,
    metabolism=1.0,
    energy_generation=0.6,

    reproduction_rule=ReproductionRule(
        reproduction_threshold=23.0,
        reproduction_cost=7.0,
        offspring_energy=6.5,
        reproduction_cooldown=2.5,
    ),

    interaction_strengths={
        0: -650.0,   # Flees Cyan
        1: -80.0,    # Slightly avoids Coral
        2: 800.0,    # Hunts Violet
        3: 220.0,    # Forms dense golden schools
    },

    feeding_rules={
        2: FeedingRule(
            rate=6.5,
            efficiency=0.68,
        ),
    },
)


species = [
    cyan_species,
    coral_species,
    violet_species,
    gold_species,
]

MAXIMUM_CONTACT_DISTANCE = 2.0 * max(
    current_species.radius
    for current_species in species
)

GRID_CELL_SIZE = max(
    SPECIES_INTERACTION_RADIUS,
    MAXIMUM_CONTACT_DISTANCE,
)

spatial_grid = SpatialGrid(domain_width=WIDTH, domain_height=HEIGHT, cell_size=GRID_CELL_SIZE)

density_field = DensityField(domain_width=WIDTH, domain_height=HEIGHT, cell_size=DENSITY_CELL_SIZE,
                             influence_radius=DENSITY_INFLUENCE_RADIUS)



pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Living Paint")

particles = []

spawn_interval = 1.0 / PARTICLE_SPAWN_RATE  # Interval of time taken between particle spawns in seconds

clock = pygame.time.Clock()
running = True

spawn_timer = 0.0
selected_species = cyan_species
grid_overlay = False
render_density_grid = False
particle_view_mode = False
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
            # Number keys select species
            if event.key == pygame.K_1:
                selected_species = cyan_species
                print(f"{selected_species.name} species selected")

            elif event.key == pygame.K_2:
                selected_species = coral_species
                print(f"{selected_species.name} species selected")

            elif event.key == pygame.K_3:
                selected_species = violet_species
                print(f"{selected_species.name} species selected")

            elif event.key == pygame.K_4:
                selected_species = gold_species
                print(f"{selected_species.name} species selected")

            elif event.key == pygame.K_g:
                grid_overlay = not grid_overlay

                if grid_overlay:
                    print("Grid overlay enabled")
                else:
                    print("Grid overlay disabled")

            elif event.key == pygame.K_d:
                render_density_grid = not render_density_grid

                if render_density_grid:
                    print("Density grid overlay enabled")
                else:
                    print("Density grid overlay disabled")

            elif event.key == pygame.K_p:
                particle_view_mode = not particle_view_mode

                if particle_view_mode:
                    print("Particle view mode enabled")
                else:
                    print("Particle view mode disabled")

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

    density_field.rebuild(particles)

    # Clear the previous frame
    screen.fill(BACKGROUND_COLOR)

    # Render the interpolated density field
    if not particle_view_mode:
        render_density_field(
            screen=screen,
            density_field=density_field,
            background_colour=BACKGROUND_COLOR,
            density_gain=DENSITY_GAIN,
        )
    else:
        render_particles(
            screen=screen,
            particles=particles,
            background_colour=BACKGROUND_COLOR
        )

    # Optional debugging overlays
    if grid_overlay:
        render_grid(
            screen,
            spatial_grid,
            GRID_OVERLAY_COLOUR,
        )

    if render_density_grid:
        render_density_grid_overlay(
            screen=screen,
            density_field=density_field,
            colour=DENSITY_GRID_COLOUR,
        )

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

    species_counts = {
        current_species.id: 0
        for current_species in species
    }

    for particle in particles:
        species_counts[particle.species.id] += 1

    count_text = " | ".join(
        f"{current_species.name}: {species_counts[current_species.id]}"
        for current_species in species
    )

    pygame.display.set_caption(
        f"Living Paint | {count_text} | Total: {len(particles)}"
    )

    # Display the completed frame
    pygame.display.flip()

# Quit the application
pygame.quit()