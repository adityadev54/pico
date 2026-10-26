# Pico
A companion that lets you request tasks on your computer from your mobile device, follow progress, and receive verified results.

Built for the Meta Global AI Developer Hackathon.

## The idea

Sometimes you need something from your computer when you only have your phone. Pico aims to bridge that gap through an agent that understands your request, uses computer tools, and checks whether the task succeeded.

## Hackathon goal

Build one reliable workflow from request to verified result.

Our propsed first workflow:
 - Request a document using a natural-language description.
 - Search permitted folders on the connected computer.
 - Ask for clarification when multiple files match.
 - Return the selected document to the mobile device.
 - Verify delivery before reporting success.

## How it will work

Phone request > agent interpretation > tool execution > verification > result

## Current status
Early development. We are defining the workflow, tool interfaces, and verification approach. Meta model integration and the new agent loop are planned hackathon work.

## Planned hackathon contributions

- Meta model integration.
- Agent planning and tool orchestration.
- Result verification.
- Failure handling and clarification.
- An integrated demo of the selected workflow.

## Development

Setup instructions will be added as we establish the development environment.

## Be careful

Do not commit API Keys, access tokens, or any local environment files.
