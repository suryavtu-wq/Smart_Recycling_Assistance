# Llama + ExecuTorch integration (required project component)

The main dashboard and image classifier can be trained and tested independently. The brief also requires a Llama-family model deployed on-device using ExecuTorch. Do not claim this requirement is complete until the exported Llama `.pte` model is actually run through an ExecuTorch runtime on the target Arm device.

## Official documentation
- ExecuTorch getting started: https://docs.pytorch.org/executorch/stable/getting-started.html
- Deploying LLMs: https://docs.pytorch.org/executorch/stable/llm/working-with-llms.html
- Exporting LLMs: https://docs.pytorch.org/executorch/stable/llm/export-llm.html

The current ExecuTorch documentation describes exporting supported Llama 2/3/3.1/3.2 models to `.pte`, then running the exported model with the ExecuTorch LLM runtime. Model access/licensing and hardware memory requirements must be checked before downloading.

## Deployment outline
1. Choose an eligible Llama-family checkpoint, for example a suitably sized Llama 3.2 model, subject to its license and target-device memory.
2. Follow the official ExecuTorch LLM export guide for the exact model and supported backend.
3. Export the model to `.pte` and obtain the matching tokenizer assets.
4. Build or use the compatible ExecuTorch LLM runner for the target Arm-based Android/Linux device.
5. Test a prompt such as: "Explain how to dispose of a clean glass bottle. Give general advice and remind the user to follow local rules."
6. Connect the runner output to the assistant interface. Keep the image classifier and text assistant as separate model pipelines.

## Why this is not enabled automatically
A `.pte` file alone is not a universal drop-in Python text-generation model. It needs the matching tokenizer, model-specific runner/runtime and target backend. The exact runner interface depends on the chosen export and device. The application therefore does not pretend that a generic Python call is a working ExecuTorch Llama integration.

## Suggested advisory prompt
"You are a waste segregation and recycling education assistant. Use the predicted material category as context when supplied. Give practical, cautious disposal and recycling guidance. Do not claim that every item in a category is recyclable. Tell the user to follow local municipal rules. For batteries, chemicals, medical waste and e-waste, direct users to authorised collection services."
