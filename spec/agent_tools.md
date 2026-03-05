This document lists a few tools that I want available to the agent. We should have a **tools package**.

Each tool should have **general code** that implements the functionality, and then expose a **decorated function** for **Pydantic** graph. The decorated function should wrap it, or have the agent do it ad hoc; maybe define a protocol or something—a bridge.

Here is a list of the tools.

## Floor Planner Tool

The first one is **floor planner**. It uses the Floor Planner Python package (<https://github.com/Nikolay-Lysenko/renovation>), and the floor planner package expects floor plan data to be input in a certain way. We are going to want the tool to take that style of input from the agent, from the user, whatever, and it is going to generate an image of the floor plan to a local file.

The expectation is that the agent can use that to visualize a room. The agent should use it in cases where the user has provided clear dimensions to the room and can create a floor plan, and ask the user for feedback on it by showing the user the floor plan image and asking them, “Is this the right thing?” or, alternatively, what their confidence is in the floor plan. The agent can send the image upstream to perform visual reasoning on it.

**Note** The library has a particular data format it expects, we'd want to represnt that in {Pydantic} and formalize the agent to generally work in that data format for room plans. See this file for example <https://github.com/Nikolay-Lysenko/renovation/blob/master/docs/demo_configs/simple_floor_plan.yml>
