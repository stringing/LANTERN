# FSE ChatRepair Artifact

## Code

We have included a copy of the source code inside the code folder

To run a demo of our tool please install the appropriate packages using Python

and then run the following command to install our package 
```
pip install -e .
```

Note since we are using OpenAI ChatGPT model, we require an API key that needs to be 
please within the Generation/ folder.

Our default setting can be ran using the following command:

```
python repair 	--folder Results/test
				--lang Java
				--dataset defects4j-1.2-single-line
				--few_shot 1
				--chain_length 3
				--total_tries 200
				--assertion_line 
				--suffix
				--key_file YOUR_OPEN_AI_KEY_FILE_NAME
```


## Patches

Please note that we have listed and compiled our correct patches within found by our tool 
inside the patches folder.

Each patch is organized based on the dataset and repair scenario used. 