import gradio as gr
import os
import json
import modules.shared as shared
import modules.chat as chat
import pickle
from modules.extensions import apply_extensions
from modules.text_generation import encode, get_max_prompt_length

# Initialize the list of keyword/memory pairs with a default pair
pairs = [{"keywords": "new keyword(s)", "memory": "new memory", "always": False},
         {"keywords": "debug", "memory": "This is debug data.", "always": False}]

memory_settings = {"position": "Before Context"}

# our select
memory_select = None


def custom_generate_chat_prompt(user_input, state, end_of_turn="", **kwargs):
    impersonate = kwargs['impersonate'] if 'impersonate' in kwargs else False
    _continue = kwargs['_continue'] if '_continue' in kwargs else False
    also_return_rows = kwargs['also_return_rows'] if 'also_return_rows' in kwargs else False
    is_instruct = state['mode'] == 'instruct'
    global pairs
    rows = [f"{state['context'].strip()}\n"]
    min_rows = 3
    
    global memory_settings

    # create out memory rows
    context_injection = []
    for pair in pairs:
        if pair["always"]:
            # Always inject it.
            context_injection.append(pair["memory"])
        else:
            # Check to see if keywords are present.
            keywords = pair["keywords"].lower().split(",")
            user_input_lower = user_input.lower()
            for keyword in keywords:
                if keyword.strip() in user_input_lower:
                    # keyword is present in user_input
                    context_injection.append(pair["memory"])
                    break  # exit the loop if a match is found

    # Add the context_injection
    context_injection_string = ('\n'.join(context_injection)).strip()

    if memory_settings["position"] == "Before Context":
        rows = [f"{context_injection_string}\n{state['context'].strip()}\n"]
    elif memory_settings["position"] == "After Context":
        rows = [f"{state['context'].strip()}\n{context_injection_string}\n"]

    # Finding the maximum prompt size
    chat_prompt_size = state['chat_prompt_size']-len(context_injection_string)
    if shared.soft_prompt:
        chat_prompt_size -= shared.soft_prompt_tensor.shape[1]

    max_length = min(get_max_prompt_length(state), chat_prompt_size)
    if is_instruct:
        prefix1 = f"{state['name1']}\n"
        prefix2 = f"{state['name2']}\n"
    else:
        prefix1 = f"{state['name1']}: "
        prefix2 = f"{state['name2']}: "

    i = len(shared.history['internal']) - 1
    while i >= 0 and len(encode(''.join(rows))[0]) < max_length:
        if _continue and i == len(shared.history['internal']) - 1:
            rows.insert(1, f"{prefix2}{shared.history['internal'][i][1]}")
        else:
            rows.insert(1, f"{prefix2}{shared.history['internal'][i][1].strip()}{state['end_of_turn']}\n")

        string = shared.history['internal'][i][0]
        if string not in ['', '<|BEGIN-VISIBLE-CHAT|>']:
            this_prefix1 = prefix1.replace('<|round|>', f'{i}')  # for ChatGLM
            rows.insert(1, f"{this_prefix1}{string.strip()}{state['end_of_turn']}\n")

        i -= 1

    if impersonate:
        min_rows = 2
        rows.append(f"{prefix1.strip() if not is_instruct else prefix1}")
    elif not _continue:
        # Adding the user message
        if len(user_input) > 0:
            this_prefix1 = prefix1.replace('<|round|>', f'{len(shared.history["internal"])}')  # for ChatGLM
            rows.append(f"{this_prefix1}{user_input}{state['end_of_turn']}\n")

        # Adding the Character prefix
        rows.append(apply_extensions("bot_prefix", f"{prefix2.strip() if not is_instruct else prefix2}"))

    while len(rows) > min_rows and len(encode(''.join(rows))[0]) >= max_length:
        rows.pop(1)

    prompt = ''.join(rows)
    if also_return_rows:
        return prompt, rows
    else:
        return prompt


def save_pairs():
    global pairs
    if shared.character is not None and shared.character != "None":
        filename = f"characters/{shared.character}.json"
    else:
        filename = "extensions/complex_memory/saved_memories.json"

    # read the current character file
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            # Load the JSON data from the file into a Python dictionary
            data = json.load(f)
    else:
        data = {}

    # update the character file to include or update the memory
    data["memory"] = pairs

    # write the character file again
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

    # with open(f"extensions/complex_memory/{filename}", 'wb') as f:
    #     pickle.dump(pairs, f)


def load_pairs():
    global pairs
    filename = ""

    # check to see if old pickle file exists, and if so, load that.
    if shared.character is not None and shared.character != "None":
        filename = f"{shared.character}_saved_memories.pkl"
        if os.path.exists(f"extensions/complex_memory/{filename}"):
            print(f"Found old pickle file.  Loading old pickle file {filename}")
            with open(f"extensions/complex_memory/{filename}", 'rb') as f:
                print("Getting memory.")
                pairs = pickle.load(f)
                print(f"pairs: {pairs}")
            print(f"Removing old pickle file {filename}")
            os.remove(f"extensions/complex_memory/{filename}")
            print("Saving data into character file.")
            save_pairs()
            print("Conversion complete.")
            return  # we are done here.

    # load the character file and get the memory from it, if it exists.
    try:
        if shared.character is not None and shared.character != "None":
            filename = f"characters/{shared.character}.json"
        else:
            filename = "extensions/complex_memory/saved_memories.json"

        # read the current character file
        with open(filename, 'r') as f:
            # Load the JSON data from the file into a Python dictionary
            data = json.load(f)

            if "memory" in data:
                pairs = data["memory"]
            else:
                print(f"Unable to find memories in {filename}.  Using default.")
                pairs = [{"keywords": "new keyword(s)", "memory": "new memory", "always": False}]

    except FileNotFoundError:
        print(
            f"--Unable to load complex memories for character {shared.character}.  filename: {filename}.  Using defaults.")
        pairs = [{"keywords": "new keyword(s)", "memory": "new memory", "always": False}]

    # Make sure old loaded data is updated
    for pair in pairs:
        if "always" not in pair:
            pair["always"] = False


def save_settings():
    global memory_settings
    filename = "extensions/complex_memory/settings.json"

    with open(filename, 'w') as f:
        json.dump(memory_settings, f, indent=2)


def load_settings():
    global memory_settings
    filename = "extensions/complex_memory/settings.json"

    try:
        with open(filename, 'r') as f:
            # Load the JSON data from the file into a Python dictionary
            data = json.load(f)

        if data:
            memory_settings = data

    except FileNotFoundError:
        memory_settings = {"position": "Before Context"}

    return memory_settings["position"]


def load_character_complex_memory_hijack(character_menu, name1, name2, mode):
    # load the character like normal
    result = chat.load_character(character_menu, name1, name2, mode)

    # Our code
    load_pairs()

    # return the result of normal load character
    return result


def pairs_loaded():
    global pairs

    select = gr.Dropdown.update(choices=[pair["keywords"] for pair in pairs], value=pairs[-1]['keywords'])

    return select


def setup():
    load_settings()


def ui():
    global pairs
    global memory_select

    # And we need to load any saved memories for the default character
    load_pairs()

    # Function to update the list of pairs
    def update_pairs(keywords, memory, always, memory_select):
        for pair in pairs:
            if pair["keywords"] == memory_select:
                pair["keywords"] = keywords
                pair["memory"] = memory
                pair["always"] = always
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
                always = gr.Checkbox.update(value=pair["always"])
                return [keywords, memory, always]

        # Didn't find it, so return nothing and update nothing.
        return
    with gr.Accordion("", open=True):
        t_m = gr.Tab("Memory", elem_id="complex_memory_tab_memory")
        with t_m:
            # Dropdown menu to select the current pair
            memory_select = gr.Dropdown(choices=[pair["keywords"] for pair in pairs], label="Select Memory",
                                        elem_id="complext_memory_memory_select", multiselect=False)

            # Textbox to edit the keywords for the current pair
            keywords = gr.Textbox(lines=1, max_lines=3, label="Keywords", placeholder="Keyword, Keyword, Keyword, ...")

            # Textbox to edit the memory for the current pair
            memory = gr.Textbox(lines=3, max_lines=7, label="Memory")

            # Checkbox to select if memory is always on
            always = gr.Checkbox(label="Always active")

            # make the call back for the memory_select now that the text boxes exist.
            memory_select.change(update_ui, memory_select, [keywords, memory, always])
            keywords.submit(update_pairs, [keywords, memory, always, memory_select], memory_select)
            keywords.blur(update_pairs, [keywords, memory, always, memory_select], memory_select)
            memory.change(update_pairs, [keywords, memory, always, memory_select], None)
            always.change(update_pairs, [keywords, memory, always, memory_select], None)

            # Button to add a new pair
            add_button = gr.Button("add")
            add_button.click(add_pair, None, memory_select)

            # Button to remove the current pair
            remove_button = gr.Button("remove")
            remove_button.click(remove_pair, memory_select, memory_select).then(update_ui, memory_select,
                                                                                [keywords, memory])

        t_s = gr.Tab("Settings", elem_id="complex_memory_tab_settings")
        with t_s:
            position = gr.Radio(["Before Context", "After Context"],
                                value=memory_settings["position"],
                                label="Memory Position in Prompt")
            position.change(update_settings, position, None)

    # We need to hijack load_character in order to load our memories based on characters.
    # shared.gradio['character_menu'].change(load_character_complex_memory_hijack,
    #                                        [shared.gradio['character_menu'], shared.gradio['name1'],
    #                                         shared.gradio['name2']],
    #                                        [shared.gradio['name2'], shared.gradio['context'],
    #                                         shared.gradio['display']]).then(pairs_loaded, None, memory_select)

    shared.gradio['character_menu'].change(load_character_complex_memory_hijack,
                                           [shared.gradio[k] for k in ['character_menu', 'name1', 'name2', 'mode']],
                                           [shared.gradio[k] for k in ['name1', 'name2', 'character_picture', 'greeting', 'context', 'end_of_turn', 'display']]).then(pairs_loaded, None, memory_select)
    # Return the UI elements wrapped in a Gradio column
    # return c


def update_settings(position):
    global memory_settings
    memory_settings["position"] = position
    save_settings()


def add_pair():
    global pairs
    found = False
    for pair in pairs:
        if pair["keywords"] == "new keyword(s)":
            found = True
            break

    if not found:
        pairs.append({"keywords": "new keyword(s)", "memory": "new memory", "always": False})

    select = gr.Dropdown.update(choices=[pair["keywords"] for pair in pairs], value=pairs[-1]['keywords'])

    return select


def remove_pair(keyword):
    global pairs
    for pair in pairs:
        if pair['keywords'] == keyword:
            pairs.remove(pair)
            break
    if not pairs:
        pairs = [{"keywords": "new keyword(s)", "memory": "new memory", "always": False}]

    select = gr.Dropdown.update(choices=[pair["keywords"] for pair in pairs], value=pairs[-1]['keywords'])

    return select
