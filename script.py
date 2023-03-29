import gradio as gr
import modules.shared as shared
import modules.chat as chat
import pickle

# Initialize the list of keyword/memory pairs with a default pair
pairs = [{"keywords": "new keyword(s)", "memory": "new memory"}, {"keywords": "debug", "memory": "This is debug data."}]

# our select
memory_select = None


def save_pairs():
    global pairs
    if shared.character is not None and shared.character != "None":
        filename = f"{shared.character}_saved_memories.pkl"
    else:
        filename = "saved_memories.pkl"

    with open(f"extensions/complex_memory/{filename}", 'wb') as f:
        pickle.dump(pairs, f)


def load_pairs():
    global pairs
    print("--debug in load_pairs")
    try:
        if shared.character is not None and shared.character != "None":
            filename = f"{shared.character}_saved_memories.pkl"
        else:
            filename = "saved_memories.pkl"

        with open(f"extensions/complex_memory/{filename}", 'rb') as f:
            pairs = pickle.load(f)

    except FileNotFoundError:
        print(
            f"--Unable to load complex memories for character {shared.character}.  filename: {filename}.  Using defaults.")
        pairs = [{"keywords": "new keyword(s)", "memory": "new memory"}]

    print(f"pairs: {pairs}")


def load_character_complex_memory_hijack(character_menu, name1, name2):
    # load the character like normal
    result = chat.load_character(character_menu, name1, name2)

    # Our code
    load_pairs()

    # return the result of normal load character
    return result


def pairs_loaded():
    global pairs

    select = gr.Dropdown.update(choices=[pair["keywords"] for pair in pairs], value=pairs[-1]['keywords'])

    return select


def ui():
    global pairs
    global memory_select

    # And we need to load any saved memories for the default character
    load_pairs()

    # Function to update the list of pairs
    def update_pairs(keywords, memory, memory_select):
        for pair in pairs:
            if pair["keywords"] == memory_select:
                pair["keywords"] = keywords
                pair["memory"] = memory
                break

        # save the changes
        save_pairs()

        select = gr.Dropdown.update(choices=[pair["keywords"] for pair in pairs], value=keywords)
        return select

    # Function to update the UI based on the currently selected pair
    def update_ui(keyword_value):
        for pair in pairs:
            if pair["keywords"] == keyword_value:
                keywords = gr.Textbox.update(value=pair["keywords"])
                memory = gr.Textbox.update(value=pair["memory"])
                break
        return [keywords, memory]

    c = gr.Column(elem_id="complex_memory")
    with c:
        # Dropdown menu to select the current pair
        memory_select = gr.Dropdown(choices=[pair["keywords"] for pair in pairs], label="Select Memory",
                                    elem_id="complext_memory_memory_select", multiselect=False)

        # Textbox to edit the keywords for the current pair
        keywords = gr.Textbox(lines=1, max_lines=3, label="Keywords")

        # Textbox to edit the memory for the current pair
        memory = gr.Textbox(lines=3, max_lines=7, label="Memory")

        # make the call back for the memory_select now that the text boxes exist.
        memory_select.change(update_ui, memory_select, [keywords, memory])
        keywords.submit(update_pairs, [keywords, memory, memory_select], memory_select)
        keywords.blur(update_pairs, [keywords, memory, memory_select], memory_select)
        memory.change(update_pairs, [keywords, memory, memory_select], None)

        # Button to add a new pair
        add_button = gr.Button("add")
        add_button.click(add_pair, None, memory_select)

        # Button to remove the current pair
        remove_button = gr.Button("remove")
        remove_button.click(remove_pair, memory_select, memory_select).then(update_ui, memory_select,
                                                                            [keywords, memory])

    # We need to hijack load_character in order to load our memories based on characters.
    shared.gradio['character_menu'].change(load_character_complex_memory_hijack,
                                           [shared.gradio['character_menu'], shared.gradio['name1'],
                                            shared.gradio['name2']],
                                           [shared.gradio['name2'], shared.gradio['context'],
                                            shared.gradio['display']]).then(pairs_loaded, None, memory_select)

    # Return the UI elements wrapped in a Gradio column
    return c


def add_pair():
    global pairs
    found = False
    for pair in pairs:
        if pair["keywords"] == "new keyword(s)":
            found = True
            break

    if not found:
        pairs.append({"keywords": "new keyword(s)", "memory": "new memory"})

    select = gr.Dropdown.update(choices=[pair["keywords"] for pair in pairs], value=pairs[-1]['keywords'])

    return select


def remove_pair(keyword):
    global pairs
    for pair in pairs:
        if pair['keywords'] == keyword:
            pairs.remove(pair)
            break
    if not pairs:
        pairs = [{"keywords": "new keyword(s)", "memory": "new memory"}]

    select = gr.Dropdown.update(choices=[pair["keywords"] for pair in pairs], value=pairs[-1]['keywords'])

    return select
