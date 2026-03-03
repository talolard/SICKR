This directory contains, or will contain, an educational project that I’m doing with my wife, Maria, where we’re going to learn to build an app together using AI.

The purpose of the app is to take a dataset of IKEA furniture that has descriptions, dimensions, and pricing, and create a kind of semantic search.

We’re going to use GCP, the new Gemini embedding model to embed the rows of the dataset in some clever ways, and then create a search interface with the idea that users can do semantic search, like:

- “Show me all L-shaped couches where the long side is 100 centimeters.”
- “Show me wall-mounted lighting units that are going to fill a long and narrow dark hallway.”

Put in the Palladium. That was the best dish for it.

This init document gives you a general sense of what we want to achieve and a bit of the how.

I’m going to ask you to scaffold the project in the following way:

You’ll write an agents.md and capture our practices.

We use UV for Python management. Virtual envs configure everything in pyproject. A heavy use of ruff for linting, so make sure that’s configured to be very thorough and run both the lint and the format on save.

Likewise, we use Facebook’s new type checker, pyrefly, P-Y-R-E-F-L-Y, and we want that deeply integrated with your coding workflow. We’re using VS Code, so make sure that’s configured with the tooling we mentioned.

We’re going to use pytest for testing. We’re going to be using the Google GCP APIs and Python packages to work.

In terms of a directory structure, we should follow a source/test layout: one directory for source, one directory for tests, and then make sure that the environment is configured so that we can run the modules with UV without referencing source, etc., and tests work.

We’re going to want a local way to store the dataset: the raw data, the vectors that we get, and user queries that come in.

We’re going to want logging standards for debugging.

We’re going to want to use some re reangor workflow from Hugging Face.

Our local development environment is on a Mac M1, so we can use MPS, and maybe later we’ll go to a GPU.

In terms of Git, this computer has two Git accounts set up, so I want everything in this project to be done using my public Git account, not my work one. That would be the Talo Lard user. There’s a configured SSH key. Then our SSH config has some configuration for going to that host, although I noticed that sometimes the accounts get messed up.

So it would be great if not only did you mention that in the agent, but that the git config or whatever for this project was consistently configured for my identity.

You’re going to be but an idea that we’re going to be able to do it.

I’d like to have directories for planning and for docs. I would like agents to write their plan in markdown files under planned, and at the end of a task to add or update documentation in docs.

Under docs, there should be an index.md file that has an external docs section that will populate with external docs, and there should be a data folder where we have our base data.

So, reading this document, please generally generate a new document init2.md that has the sequence of tasks, in order, that you’ll do, that we should do, to fulfill this, from environment setup to everything short of actually starting development.



The last note is that this document has been generated through dictation, and so if some dictation is wrong, you can stop and ask me for clarification, or if there’s a word that kind of fits funnily. So don’t make assumptions. Ask me as you generate init2. 

A few other things I’d like to make sure that you capture. I should probably store the data in DuckDB and/or SQLite. When writing SQL, keep SQL in .sql files. I don’t really like the pattern of writing Python to access the database if there’s no benefit to it, so prefer writing the SQL files and various pragmas, and using DuckDB’s CLI. You can create the DuckDB file and configure it. You can get rid of the IKS CSV after you loaded it; I have a spare copy. It would be good if you documented, of course, the columns and database structure, and maintained that as it evolved. 