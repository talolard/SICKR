# Changelog

## [0.2.1](https://github.com/talolard/SICKR/compare/v0.2.0...v0.2.1) (2026-03-27)


### Bug Fixes

* **ci:** lint workflows and fix release publish shell parsing ([78e6ac9](https://github.com/talolard/SICKR/commit/78e6ac9c7b9d80f3e2993087d4f08e863dfdc01b))

## [0.2.0](https://github.com/talolard/SICKR/compare/v0.1.0...v0.2.0) (2026-03-27)


### Features

* **deploy:** add aws deployment stack ([4561b3b](https://github.com/talolard/SICKR/commit/4561b3b6821dc0d1ea85dcb1f895e293fcfe7bdc))


### Bug Fixes

* **deploy:** accept healthy backend rollout before full drain ([#110](https://github.com/talolard/SICKR/issues/110)) ([d49a580](https://github.com/talolard/SICKR/commit/d49a580f686f3523f4291bc8dedbc8a3097a184e))
* **deploy:** close remaining ECS release blockers ([#126](https://github.com/talolard/SICKR/issues/126)) ([9363256](https://github.com/talolard/SICKR/commit/9363256d7986c1ce16c52390dd0f21c0d6591b3c))
* **deploy:** detect bad Alembic state and incomplete backend rollouts ([#117](https://github.com/talolard/SICKR/issues/117)) ([ede1641](https://github.com/talolard/SICKR/commit/ede164107c262675a7a769aba46b9c05e3d2c46a))
* **deploy:** enforce release branch governance ([#119](https://github.com/talolard/SICKR/issues/119)) ([2b24266](https://github.com/talolard/SICKR/commit/2b2426688308a81e33324e2770a99a2fadf8445f))
* **deploy:** harden manual ecs deploy workflow ([#108](https://github.com/talolard/SICKR/issues/108)) ([9412312](https://github.com/talolard/SICKR/commit/941231244c4638dbc9893adea32731cd1a858be9))
* **deploy:** merge live runtime hardening into main ([#107](https://github.com/talolard/SICKR/issues/107)) ([6779c5c](https://github.com/talolard/SICKR/commit/6779c5c2192d92a37e24a89be2db690f8cd2e369))
* **deploy:** route backend APIs directly and unblock release publish ([bc895c6](https://github.com/talolard/SICKR/commit/bc895c6137a2e3a75108339a561dfd60e442491d))
* **deploy:** run packaged deploy modules correctly ([#109](https://github.com/talolard/SICKR/issues/109)) ([323bd35](https://github.com/talolard/SICKR/commit/323bd353f4ca274231b82f7f06a2ebfd101970a9))
* **deploy:** validate release publish identity ([#118](https://github.com/talolard/SICKR/issues/118)) ([2d9ff70](https://github.com/talolard/SICKR/commit/2d9ff70083d9d3a4dfcc8da5ea3265016dcad5f1))
* **release:** move release automation onto main and tags ([#128](https://github.com/talolard/SICKR/issues/128)) ([06ac337](https://github.com/talolard/SICKR/commit/06ac337bc503e7646234476a8d5ac60a2fef2db9))
* **release:** move release-please bootstrap to March 25 baseline ([#130](https://github.com/talolard/SICKR/issues/130)) ([1a7976c](https://github.com/talolard/SICKR/commit/1a7976c7b66b6d1c1195007158dc3bc66f2960f2))
* **ui:** route deployed backend proxy traffic through ALB root ([#113](https://github.com/talolard/SICKR/issues/113)) ([74cd241](https://github.com/talolard/SICKR/commit/74cd2418d379008cf1d38d6900f2f8d5528d73b5))

## Changelog

All notable changes to this project will be recorded in this file.
