# LINUX VERSION

# Overview:
'''
 Develop a randomized policy (choose direction randomly)
 -- Effectively acheived by setting random values
 Calculate consistent state values for this policy.
 Develop a new policy that is greedy with respect to these state values.
 Loop.
 Each policy is guaranteed to be a strict improvement over the previous,
 except in the case in which the optimal policy has already been found.
'''

# NOTES: 
# We assume that we know the transition function
# -- Given state, action, we can determine the next state
# -- Later we want to relax this assumption (use probabilities)
# We assume that we know the reward function

# State order is this: [pos, height, towardsCent]

# Import:
import numpy as np
# For timestamp of file saved
import time     
import datetime
# To allow folder creation
import os

# Input: state variables
# Output: value of state
def createValNetwork(dimState, numHidden):
    # Build a feed forward neural network (with one hidden layer)
    from pybrain.structure import SigmoidLayer, LinearLayer
    from pybrain.tools.shortcuts import buildNetwork
    valNet = buildNetwork(dimState, # Number of input units
                       numHidden,   # Number of hidden units 
                       1, 	        # Number of output units
                       bias = True,
                       hiddenclass = SigmoidLayer,
                       outclass = LinearLayer # Allows for a large output
                       )	
    return valNet

# Input: state variables
# Output: classification of actions (one hot encoded)
def createPolNetwork(dimState, numHidden, numAct):
     # Build a feed forward neural network (with a single hidden layer)
    from pybrain.structure import SigmoidLayer, SoftmaxLayer
    from pybrain.tools.shortcuts import buildNetwork
    polNet = buildNetwork(dimState, # Number of input units
                       numHidden, 	# Number of hidden units
                       numAct, 	        # Number of output units
                       bias = True,
                       hiddenclass = SigmoidLayer,
                       outclass=SoftmaxLayer # Outputs are in (0,1), and add to 1
                       )	
    return polNet

# Plot estimated value function 
# evalDir = list of directions we can travel in
def graphValues(valNet, evalDir, policyEvalStates, nextStateList, nextValList, maxX):
    import matplotlib.pyplot as plt
    
    # Create distance linspace for plotting
    start = 0; stop = 10;
    dist = np.linspace(start, stop, num=60)  
    
    # Determine value at multiple heights
    valList = [] # List of value estimates
    heightInd = 0 # Which height we're working with
    for height in [0.5, 0.2, 0, -0.2, -0.5]: # Desired heights     
        valList.append([])
        for pos in dist:              
            towardsCent = 0 # Desired direction to evaluate value network at
            val = valNet.activate([pos, height, towardsCent])[0] 
            valList[heightInd].append(val)            
        plt.plot(dist,valList[heightInd], label = height)
        heightInd = heightInd + 1
    #plt.legend()
    plt.xlim([0,maxX])
    plt.xlabel('Distance')
    plt.ylabel('Value')
    plt.title('Value Function, Direction = ' + str(towardsCent))
    
    # Plot data used to train policy network
    trainValToPlot = []
    trainDistToPlot = []    
           
    # Plot data used for training policy network
    # State order is this: [pos, height, towardsCent]
    i = 0   # Which training example
    for state in nextStateList:
        towardsCent = 0 # Plot only training examples going towards thermal  
        heightVal = 0   # Plot only examples at zero height
        if (state[2] == towardsCent and state[1] == heightVal):
            trainValToPlot.append(nextValList[i])
            trainDistToPlot.append(state[0])
        i = i + 1
    plt.plot(trainDistToPlot, trainValToPlot, 'o')
    
    # Indicate where our training examples are
    for state in policyEvalStates:
        stateDist = state[0]
        plt.axvline(stateDist)
    
    #plt.legend()
    
    # Don't show the plot - save the plot (Linux)
    # plt.draw()   

def graphPolicy(polNet, policyEvalStates, actList, maxX):
    import matplotlib.pyplot as plt
    start = 0; stop = 10;
    dist = np.linspace(start, stop, num=60) # Where to evaluate policy
    
    prefToward = []
    prefAway = []
    preOrb = []
    # Print how much we like the different actions
    heightVal = 0       # What height to evaluate the policy at
    towardsCentVal = 0  # What facing direction to evaluate the policy at
    for pos in dist:
        height = heightVal   
        towardsCent = towardsCentVal
        preferences = polNet.activate([pos, height, towardsCent])
        # Record preference for different options
        prefToward.append(preferences[0])  
        prefAway.append(preferences[1])      
        preOrb.append(preferences[2])   
    plt.plot(dist,prefToward, label = 'Move towards')
    plt.plot(dist,prefAway, label = 'Move away')
    plt.plot(dist,preOrb, label = 'Orbit')
    plt.xlabel('Distance')
    plt.ylabel('Preference')
    plt.xlim([0,maxX])
    plt.ylim([-0.1,1.1])
    
    plt.title('Policy at h=' + str(heightVal))
    plt.legend()

    # Indicate where our training examples are
    for state in policyEvalStates:
        stateDist = state[0]
        plt.axvline(stateDist)
    
    # Indicate the training example choices (stored in actList)
    trainChoice = []
    trainDist = []
    i = 0
    relActs = []    
    for state in policyEvalStates:  
        # Store only training examples for desired height and direction
        if (state[1] == heightVal and state[2] == towardsCentVal):
            trainChoice.append(actList[i])
            relActs.append(actList[i])
            trainDist.append(state[0])
        i = i + 1
    plt.plot(trainDist, trainChoice, 'o')
    # print('All acts: \n', actList)
    # print('Rel actlist: \n', relActs)    
    
def mainModelBased():
    # Time stamp this run:
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%m-%d %H-%M-%S')

    # 1. Create a random value function
    dimState = 3 # Number of state variables used in discretized training examples (position from thermal, height, direction (towards or away center))
    numHiddenVal = 20 # Number of hidden neurons
    valNet = createValNetwork(dimState,numHiddenVal)  # Using two hidden layers for precision  
    
    # 2. Create a random policy network
    numHiddenPol = 20 # Number of hidden neurons
    numAng = 2 # Towards or away from thermal center   
    # numAct = numAng # If no orbiting
    numAct = numAng + 1 # Number of actions (additional action is for orbit - preserve distance from center)
    polNet = createPolNetwork(dimState, numHiddenPol, numAct)       
    
    
    # 3. Update values based on current policy
    # The policy is greedy with respect to the value estimates
    
    # 3a. Determine subset of state to update on
    # It isn't practical to visit every possible state
    # Instead, we will work on a discretized version of the state space, and trust to the neural network for interpolation    
    # Here we set the states used to update the policy
    start = 0
    stop = 10    
    maxX = stop # For plotting
    evalDist = np.linspace(start, stop, num=8)
    evalHeight = [0, 0.5] # Avoid segmenting on height until shown to be necessary
    evalDir = [0]#[0,1] # 0 is pointing towards thermal center, 1 is pointing away from thermal center
    
    import itertools
    policyEvalStates = list(itertools.product(evalDist,evalHeight, evalDir)) # Takes cartesian product
    
    # Print initial policy
    printPolVal = 0
    if (printPolVal == 1):
        print('Initial policy:')
        print('Choice \t State')
        for state in policyEvalStates:
            print(np.argmax(polNet.activate(state)), '\t', state)   
    
    import sys; sys.stdout.flush()
        
    # Go back and forth between value and policy
    import evalPolicy
    vMaxAll = 0.5   # We require values to stop changing by any more than this amount before we return the updated values
    stepSize = 0.1  # How far the airplane moves each time (needed to predict next state, make policy decisions)
    thermRadius = 3 # Standard deviation of normal shaped thermal   
    
    numLearn = 100 # Number of times to repeat learning cycle
    
    # Learning iterations loop
    for i in range(numLearn):  
        print('Start iteration: ', str(i))
        # Make values consisstent with policy
        valNet = evalPolicy.evalPolicy(valNet,polNet,policyEvalStates,vMaxAll, stepSize, thermRadius)   
        
        # 4. Update policy based on current values 
        import updatePolicy
        (polNet, nextStateList, nextValList, actList) = updatePolicy.makeGreedy(valNet, polNet, policyEvalStates,numAct,stepSize, thermRadius, numHiddenPol)
        
        if (printPolVal == 1):
            # Print update value network on a few sample points
            print('Updated value function:')
            print('Value \t State')
            for state in policyEvalStates:
                print(valNet.activate(state), '\t', state) 
            
            # Print updated policy on a few sample points
            print('Updated policy:')
            print('Choice \t State')
            for state in policyEvalStates:
                print(np.argmax(polNet.activate(state)), '\t', state)   
                
        # Display the estimated value function and policy
        clearPeriod = 1
        if (i == 0):
            import matplotlib as mpl
            mpl.use('Agg') # Allows us to save image instead of displaying
            
            import matplotlib.pyplot as plt              
            plt.figure()              

        # Periodically clear plot
        if (i % clearPeriod == 0 and i != 0):
            plt.clf() 
                   
        # Plot value network
        # valList is the values used by the policy network
        plt.subplot(2, 1, 1)
        graphValues(valNet, evalDir,policyEvalStates, nextStateList, nextValList, maxX)
        
        # Plot policy network
        plt.subplot(2, 1, 2)
        graphPolicy(polNet,policyEvalStates, actList, maxX)        
        
        # Save an image of the results
        if (i % 5 == 0):
            # Store photos one directory up, with a time stamp and an i value
            saveDir = '/home/david.egolf/debugImages/' + st + '/'
            if not os.path.isdir(saveDir): # Make the directory if needed
                os.makedirs(saveDir)
            plt.savefig(saveDir + 'iter = ' + str(i))        

mainModelBased()



