## Docker Dependency Brain Dump

The spec describes rough goals for setting up Docker for a development environment. The problems I want to solve are mostly around having multiple agents working concurrently with different worktrees and needing access to our dependencies.

Currently, our dependencies are DuckDB, maybe SQLite (I’m not even sure), and Milvus Lite for vector search. Those are two somewhat external services that we use that maintain state in files. We also have IKEA images that we’re currently serving through FastAPI, but locally it’d probably be easier to serve them in a more centralized manner.

Currently, each worktree points back to the original worktree for copies from the original registry for some of those dependencies, and it creates quite a mess. An additional problem is that DuckDB only allows one writer. So we really do have to copy the database over, and we’re having a bunch of issues with the WAL log, etc.

The end state I’d like to be at is that we’ve moved the database from DuckDB to Postgres, and we have that Postgres in Docker. It’s been a while since I did Docker, but presumably we would have a data volume with the Postgres data there, similar to the way we have the `main.dkb` snapshot now. On startup, it would run any migrations needed.

Then each worktree (each agent), when it spins up a worktree, would be able to spin up its own Postgres that’s pre-populated in a known way, and we’d have some command for that. We would also have, in CI, some build step that detects changes to the base data or changes to the migrations and rebuilds the base image for Postgres. But the base image needs to be reset further. I am open to proposals on exactly what it is: is it just Postgres and then we have a data volume, or do we have some other settings? I’d be happy for input.

On the Milvus side similarly: we’d want to have Milvus in Docker. For the time being, the data there is static, so we don’t write there; it’s really just storing the catalog in a vectorized way. At any rate, it would be good to have it in Docker. For simplicity, it is probably worth having each agent that needs it spin up its own. That’s not mandatory, but we could probably get away with one Milvus for all worktrees and just making that known if spinning up one per worktree is too heavy.

Then again, we’d want some process describing how we build a base image with the data pre-populated, or do we mount it as a volume that Milvus starts up from? Either is fine. If it’s a volume and we have to copy over that data each time for each worktree, it kind of defeats part of the purpose.

For the images, I’m open, but do we know what good practices are for serving a lot of static files across multiple worktrees? Surely we don’t want to build the images into the containers, but maybe we’d want to put Nginx in front of it—or maybe not; maybe that doesn’t make sense.

There’s a third topic, and I need input on this before we make any decisions, but I need a clear explanation: DevContainers. Would those make it an easier and more consistent way for us to define an environment than just having a bunch of containers in Docker Compose?

I’d like you to read this, do some research about it, and write me a section below. Based on our current state and the research you’ve done, write what we should be doing: a rough spec, how it solves each of our problems, pros and cons, and answers to all the questions I stated above.
