1. Use Three.js to render floor plans and 3D plans, with the ability for the user to capture screenshots and send them to the model.

2. Create graphs for specific modes and goals. For instance, there is a mode or goal of discovering the room dimensions before planning. Another mode is discovering user goals. Another mode is analyzing pictures to understand the current situation, which could come before or feed into generating floor plans, but also to get a sense of what is there. It would be based on using computer vision and analysis.

In each of these, fundamentally an agent is going to be interacting with some broad context and then iteratively working with tools to try to reach and validate a conclusion. We would want to manage those independent flows without each one having and filling in the shared history, message history.

1. # Visual Workspace

Currently, in the UI, we show a chat box, but we should be showing the user representation of what we know. That is a visualization of the latest room dimensions, a list of preferences, and maybe later we will have a few related projects.

For example, I am doing the bedroom and the living room. We could also show some memory about the user’s taste. Etc.

# User Intents / Goals

----

## Advice - text only

**essence:** user wants advice on a small concept and just asks with some text

### Examples

    - I have some space under my bed I want to use as storage
    - What are good plants I can put in my hallway that doesn't have much natural light?

### Basic Workflow

- Do an intial search in the catalog and present some options. Then ask the user questions to discover constraints (size of room, budget etc) and preferences (style, colors, etc). Decide if a new search or delegating to another flow.

## Advice - text+ images

**essence:** user has a specific situation they want advice on, and they can upload images to show the situation

### Examples

    - User uploads photo of their bed from some angle and asks for storage ideas
    - User uploads photo of their hallway and asks for plant recommendations
    - User uploads photo of their living room and asks for clutter reduction ideas

### Basic Workflow

- Use the image analysis tools to understnd room structure (depth estimation, photogrammetry, object detection, segmentation etc).
- Ask user what bothers them / what they feel. match that with findings .
- Propose conceptual solutions (you have laundry on the floor -> having an accessible hamper or a spot to put clothes for tommorow might help reduce that) and if the user likes it propose specific products.
-

## Goal and constraint oriented planning

**Essense** User has a room in mind and a (possibly vague) goal, we unwrap the users constraints and preferences and then generate a plan to achieve that goal within those constraints,
by preparing a bundle of products from the catalog and where each one sits in the room

### Examples

- Help me refurnish my sons room , he's 7 and needs A,B,C. Here are some pictures and rough meaurements
- Our long hallway is dark, the end of it is cluttered, we have dogs so no rugs but we'd like to reduce how much sound carries. I want to spend XX tops

### Basic Workflow
- Use the image analysis tools to understnd room structure (depth estimation, photogrammetry, object detection, segmentation etc).
- Ask the user about measurements and generate floor plan 
- Ask about existing items / preferences / goals 
