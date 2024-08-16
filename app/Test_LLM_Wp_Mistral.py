import pandas as pd
import numpy as np
from agents.agents import MoralAgent
from prompts.prompts import fault_predicton_system_prompt
from prompts.prompts import fault_predicton_guided_json
import json

# from agent_graph.graph import create_graph, compile_workflow



# server = 'ollama'
# model = 'llama3:instruct'
# model_endpoint = None

server = 'openai'
model = 'gpt-4o'
model_endpoint = None

# server = 'vllm'
# model = 'meta-llama/Meta-Llama-3-70B-Instruct' # full HF path
# model_endpoint = 'https://kcpqoqtjz0ufjw-8000.proxy.runpod.net/' 
# #model_endpoint = runpod_endpoint + 'v1/chat/completions'
# stop = "<|end_of_text|>"

iterations = 40

# Load the dataset
data = pd.read_csv('modified_faulty_data_Test.csv')
data['text_representation'] = data.apply(lambda row: f"Vehicle {row['coreData_id']} Time {row['t']} Speed {row['coreData_speed']}", axis=1)

# Add new columns for LLM's label and analysis
data['Label by LLM'] = 0
data['LLM Analysis'] = ""

# Filter data for specific vehicle IDs
vehicle_ids_to_analyze = [8199461, 8700840]
filtered_data = data[data['coreData_id'].isin(vehicle_ids_to_analyze)]

# Organize data by vehicle ID and sort by time in ascending order
grouped = filtered_data.groupby('coreData_id')
results = []

# Define a refined prompt for the Mistral model
def create_prompt(history, subsequent_reading=None):
    prompt =""
    for entry in history:
        prompt += f"{entry}\t"
    
    if subsequent_reading:
        (
            "Given this historical data, analyze the following reading and determine if it represents a normal speed or a fault:\n"
            f"{subsequent_reading}\n"
            
        )
    return prompt

# A function to pre-process and filter out minor changes before passing to LLM
def filter_small_changes(history):
    filtered_history = []
    for i in range(1, len(history)):
        prev_speed = float(history[i-1].split()[3])
        curr_speed = float(history[i].split()[3])
        # Check to avoid division by zero
        if prev_speed == 0:
            if curr_speed == 0:
                change = 0  # No change if both are zero
            else:
                change = float('inf')  # Consider any non-zero speed as a significant change
        else:
            change = abs(curr_speed - prev_speed) / prev_speed
        
        if change >= 0.10:  # 10% change threshold
            filtered_history.append(history[i])
        else:
            filtered_history.append(history[i])
    return filtered_history

if __name__ == "__main__":



    # Uncoment below to run with OpenAI
    # model_service = OpenAIModel
    # model_name = 'gpt-3.5-turbo'
    # stop = None

    # Uncomment below to run with Ollama
    
    server = 'ollama'
    models = ['llama2:latest']
    model_endpoint = None
    for model in models:
        agent = MoralAgent(
                model=model,
                server=server,
                guided_json=fault_predicton_guided_json,
                model_endpoint=model_endpoint,
                temperature=0 )
        print("started working")

    # Iterate over each unique vehicle ID
        for vehicle_id, group in grouped:
            print(f"Processing vehicle ID: {vehicle_id}")
            group_sorted = group.sort_values(by='t')  # Sort by time column 't' in ascending order
            texts = group_sorted['text_representation'].tolist()
            context_texts = [f"t {entry.split()[3]} coreData_speed {entry.split()[5]}" for entry in texts[:60]]  # First 60 readings as context
            context_texts = filter_small_changes(context_texts)  # Apply the filter to remove small changes
            subsequent_texts = texts[60:]  # Remaining readings for prediction
            
            # Initialize the context prompt with historical data
            context_prompt = create_prompt(context_texts)
            
            # Prepare context inputs for the model
            predictions = []
            for i, text in enumerate(subsequent_texts):
                print(f"Analyzing reading: {text}")
                prediction_prompt = create_prompt(context_texts, text)
                response=agent.invoke(
                    research_question=prediction_prompt,
                    # previous_plans=lambda: get_agent_graph_state(state=state, state_key="planner_all"),
                    prompt=fault_predicton_system_prompt
                )
                outputVal=json.loads(response.content)
                # df['Answer'][i]=outputVal['Choice']
                # print(outputVal['Choice'])
                # df.to_csv(model+'Result.csv')
                # Determine if the generated text indicates a fault
                label=outputVal['prediction']
                analysis=outputVal['analysis']
                
                predictions.append((text, label, analysis))
                
                # Update context with the most recent reading, but limit the context size to avoid overfitting
                context_texts = context_texts[1:]  # Remove the oldest entry
                context_texts.append(f"t {text.split()[3]} coreData_speed {text.split()[5]}")
                if len(context_texts) > 40:  # Limit the context to the last 40 readings
                    context_texts.pop(0)

            # Store the results in the data DataFrame in the correct sequence
            for text, label, analysis in predictions:
                idx = data[(data['coreData_id'] == vehicle_id) & (data['text_representation'] == text)].index[0]
                data.at[idx, 'Label by LLM'] = label
                data.at[idx, 'LLM Analysis'] = analysis
                print(f"Vehicle ID: {vehicle_id}, Reading: {text}, Label: {label}, Analysis: {analysis}")

        # Sort the final data by vehicle ID and time, then save the results to a new CSV file
        data_sorted = data[data['coreData_id'].isin(vehicle_ids_to_analyze)].sort_values(by=['coreData_id', 't'])
        data_sorted.to_csv(model+'Analysis_of_LLM_with_label.csv', index=False)
        
           