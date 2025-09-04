# CHANGELOG

<!-- version list -->

## Unreleased

### Documentation

- **README**: Reorder badges for better visibility
  ([`07a3452`](https://github.com/SootyOwl/yt-transcript/commit/07a34525ebf7b17998c972b33513af624342a023))


## v1.1.4 (2025-09-04)

### Chores

- **pyproject**: Update keywords and classifiers
  ([`07263ed`](https://github.com/SootyOwl/yt-transcript/commit/07263ed61eab954601419002c1a65200aedb896b))

- **pyproject**: Update project URLs and changelog settings
  ([`377c8c7`](https://github.com/SootyOwl/yt-transcript/commit/377c8c7ca3a76b00e5fd19f611e8320ba054dbcb))

- **semantic-release**: Add force release options
  ([`a9d7a8b`](https://github.com/SootyOwl/yt-transcript/commit/a9d7a8b2b6ac35a94a6d122cfad859897748e26c))

### Continuous Integration

- **semantic-release**: Enhance workflow inputs for release
  ([`053af9b`](https://github.com/SootyOwl/yt-transcript/commit/053af9b3a75d7db0405b3ad7377072fb6394d9db))

### Documentation

- **README**: Add test status badge to README
  ([`47c7d2f`](https://github.com/SootyOwl/yt-transcript/commit/47c7d2fe2bce5f618ee7a8eb4bbd437d937d2ed6))


## v1.1.3 (2025-09-04)

### Bug Fixes

- **api**: :alien: add retry logic to session configuration
  ([`440899e`](https://github.com/SootyOwl/yt-transcript/commit/440899e9fe04f6956b91e8dcea573ba0b435b19e))

- **api**: :alien: bump clientVersion in context
  ([`20cb4d3`](https://github.com/SootyOwl/yt-transcript/commit/20cb4d3bdd86c3ef3c1a685feeeee9d84247d802))

### Chores

- **dependencies**: Add pytest-repeat to dev dependencies
  ([`0661cd9`](https://github.com/SootyOwl/yt-transcript/commit/0661cd9fadc3309af79c51f3e337846db4c93c5a))

- **dependencies**: Update dev dependencies in pyproject.toml
  ([`24f4808`](https://github.com/SootyOwl/yt-transcript/commit/24f4808a816bfe6801e56f8dd9adbedc36b2ca53))

- **vscode**: Add settings for pytest configuration
  ([`6caf26b`](https://github.com/SootyOwl/yt-transcript/commit/6caf26b6f3586b1beb8cb685d711c226ba86c319))

### Refactoring

- **api**: Move session initialisation to dedicated method
  ([`320cbe4`](https://github.com/SootyOwl/yt-transcript/commit/320cbe45c4af3879c093502f82017351b2722f0d))


## v1.1.2 (2025-09-04)

### Bug Fixes

- **models**: Update type hint for __contains__ method
  ([`ab3f2d2`](https://github.com/SootyOwl/yt-transcript/commit/ab3f2d2c938fe6ac6e464e4c5a0c62552d1d589a))

### Build System

- :building_construction: migrate to uv
  ([`e84be20`](https://github.com/SootyOwl/yt-transcript/commit/e84be2029d1fd4ede7095cd57262abbae1f5f396))

### Chores

- **actions**: Add daily test github action
  ([`5cd539a`](https://github.com/SootyOwl/yt-transcript/commit/5cd539a2eeb8870947cc14106e8989182f926f70))

- **actions**: Add name for release workflow
  ([`ccf6404`](https://github.com/SootyOwl/yt-transcript/commit/ccf640481b25f974308659b651786b1ada4dd0d2))

- **actions**: Add workflow name for test runs
  ([`ae7edaf`](https://github.com/SootyOwl/yt-transcript/commit/ae7edaf4b34d00e61b3df7c64ad7dc3e909f1720))

- **actions**: Update test workflow to run on pull requests
  ([`50667a7`](https://github.com/SootyOwl/yt-transcript/commit/50667a7130b67c8a9521a315da103464154217f2))

- **deps**: Bump urllib3 from 2.4.0 to 2.5.0
  ([#1](https://github.com/SootyOwl/yt-transcript/pull/1),
  [`103a3f6`](https://github.com/SootyOwl/yt-transcript/commit/103a3f669bda9744419b29e60c9331933c93ba9d))

- **semantic-release**: Move uv setup to pyproject.toml
  ([`e209be0`](https://github.com/SootyOwl/yt-transcript/commit/e209be0575d15adc806622b6981bef21bc5a071f))

- **semantic-release**: Set up uv for build process
  ([`41d19c2`](https://github.com/SootyOwl/yt-transcript/commit/41d19c2fa8a6246d0c6e6276f024fdf3bb96b1d5))

- **semantic_release**: Add configuration for semantic release
  ([`216fb7b`](https://github.com/SootyOwl/yt-transcript/commit/216fb7b78c71f13ae8a2310877bb73aed906c472))

- **semantic_release**: Update build command for package
  ([`ba1d701`](https://github.com/SootyOwl/yt-transcript/commit/ba1d7018e6dcc93d7b7d16aa443bb9fbe9705259))

- **semantic_release**: Update main branch configuration
  ([`339d5f0`](https://github.com/SootyOwl/yt-transcript/commit/339d5f02a69b9766fe08a44a88eae192c75be0cf))

- **uv**: Update uv package and revision in lock file
  ([`ba0420d`](https://github.com/SootyOwl/yt-transcript/commit/ba0420d263d67b0bad9d531f3bf4b13be57d0f44))

- **workflow**: Add push trigger for main branch
  ([`a468d3c`](https://github.com/SootyOwl/yt-transcript/commit/a468d3cace9d7d2e597a1e97115029f2d7d05a86))

### Continuous Integration

- **tests**: Update "Run Tests" workflow to use uv for testing
  ([`b665629`](https://github.com/SootyOwl/yt-transcript/commit/b665629c7ed81d0ce39f3b9d1c4280fac1b77d0a))


## v1.1.1 (2025-06-12)

### Bug Fixes

- **models**: Broader validation of time range in Segment class
  ([`6405dc0`](https://github.com/SootyOwl/yt-transcript/commit/6405dc0d769843e78a174d25d3127c06140df089))

### Chores

- **release**: 1.1.1 [skip ci]
  ([`89a8084`](https://github.com/SootyOwl/yt-transcript/commit/89a808411f01be1656db94369574b0f6f8cd2145))


## v1.1.0 (2025-06-12)

### Chores

- Update CHANGELOG.md [skip ci]
  ([`f7a84e3`](https://github.com/SootyOwl/yt-transcript/commit/f7a84e38ab3b561c1af5b3094773f96d1c3f7a3d))

- **release**: 1.1.0 [skip ci]
  ([`5665047`](https://github.com/SootyOwl/yt-transcript/commit/56650478cfe6e9d9929456b6b46a6757ddc0295b))

### Features

- :children_crossing: enhance language containment check in LanguageList to allow checking by
  language code string
  ([`c0e76a6`](https://github.com/SootyOwl/yt-transcript/commit/c0e76a6309b6060940f1198e6a33bf21ce607bdf))


## v1.0.0 (2025-06-12)

- Initial Release
