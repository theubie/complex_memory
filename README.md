# complex_memory
A KoboldAI-like memory extension for oobabooga's text-generation-webui

Memory is currently stored in its own files and is based on the character selected. I am thinking of maybe storing them inside the character json to make it easy to create complex memory setups that can be more easily shared.

You create memories that are injected into the context for prompting based on keywords. Your keyword can be a single keyword or can be multiple keywords separated by commas. I.e.: "Elf" or "Elf, elven, ELVES". The keywords are case-insensitive. You can also use the check box at the bottom to make the memory always active, even if the keyword isn't in your input.

When creating your prompt, the extension will add any memories that have keyword matches in your input along with any memories that are marked always. These get injected at the top of the context.

Note: This does increase your context and will count against your max_tokens.

If you are looking for a more simple extenion, you can check out my simple_memory extension: https://github.com/theubie/simple_memory

Anyone wishing to help with the documentation I will give you over 9000 internet points.