# Allo IA


Voice first AI agent that turns spoken conversations into FabLab project documentation, running fully offline on low cost hardware.

## Overview

Projects built in FabLabs are rarely documented: makers focus on fabrication and seldom take the time to write down their choices, difficulties and solutions. Allo IA addresses this by replacing writing with conversation.

The user describes their project through a telephone handset. An AI agent running on a local language model conducts the interview: it asks follow up questions, identifies missing information, requests photos when relevant, and produces a structured first draft of the project documentation that the user can then enrich and export.

Speech recognition, language generation and speech synthesis all run locally on a nano computer (Raspberry Pi or NVIDIA Jetson), so no data leaves the device.

The project also includes a benchmark of hardware and lightweight AI models to identify the best trade off between quality, latency, cost and energy consumption.

## Context

Allo IA originated at October Make 2025, the annual event of RFFLabs (the French FabLab network). It is developed as a final year engineering project at IMT Atlantique, in partnership with the Edulab of University Rennes 2, and builds on the open documentation tool DoDoc.

## Status

Early development
