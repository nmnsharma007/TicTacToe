#import modules
import pygame
from pygame.locals import *
import numpy as np
import time
import copy

# in the board, 0 denotes an empty cell, 1 denotes X and 2 denotes O
def state2num(state):
    """ Function for converting 2d state matrix to a number
    Here, the matrix is written as a base 3 number of length n x n. 
    """
    num = 0
    state = state.flatten()
    for i in range(len(state)):
        num = num * 3 + state[i]
    return int(num)

def num2state(num,n=3):
    """ Function for converting the number back into a state matrix 
    denoting the state of the board
    """
    cur_state = num
    state = np.zeros((n,n),dtype=np.int64)
    for i in reversed(range(n*n)):
        rem = cur_state % 3
        row = i // n
        col = i % n
        state[row][col] = rem
        cur_state //= 3
    return state

def check_winning(state):
    """ Check if the state is a winning state
    """
    n = state.shape[0]
    temp_state = np.copy(state)
    for i in range(n):
        for j in range(n):
            if temp_state[i][j] == 2:
                temp_state[i][j] = -1
    for row in range(n):
        if np.sum(temp_state[row,:]) == n:
            return True
    for col in range(n):
        if np.sum(temp_state[:,col]) == n:
            return True
    if np.trace(temp_state) == n:
        return True
    anti_diagonal_sum = 0
    for i in range(n):
        anti_diagonal_sum += temp_state[i][n-i-1]
    return anti_diagonal_sum == n

def check_draw(state):
    """Check if state is a draw state
    """
    numX = (state == 1).sum()
    numO = (state == 2).sum()
    return numX + numO == 9

def check_losing(state):
    """ Check if the state is a losing state
    """
    n = state.shape[0]
    temp_state = np.copy(state)
    for i in range(n):
        for j in range(n):
            if temp_state[i][j] == 2:
                temp_state[i][j] = -1
    for row in range(n):
        if np.sum(temp_state[row,:]) == -n:
            return True
    for col in range(n):
        if np.sum(temp_state[:,col]) == -n:
            return True
    if np.trace(temp_state) == -n:
        return True
    anti_diagonal_sum = 0
    for i in range(n):
        anti_diagonal_sum += temp_state[i][n-i-1]
    return anti_diagonal_sum == -n

# Model the state space
num_states = 0
reduced_state = dict()
actual_state = dict()

# iterate over all states and count the valid ones
for i in range((3**9)):
    state = num2state(i)
    numX = (state == 1).sum()
    numO = (state == 2).sum()
    # if it is the agent's turn, then it is a valid state
    if numX == numO:
        # if winning state for X, its an invalid state
        if check_winning(state):
            continue
           # create a mapping between reduced state number and actual state number
           # for reducing the state space size
        reduced_state[i] = num_states
        actual_state[num_states] = i
        num_states += 1
    elif numX == numO + 1:
        if check_winning(state) and not check_losing(state): # win state
            reduced_state[i] = num_states
            actual_state[num_states] = i
            num_states += 1
        elif numX + numO == 9 and not check_losing(state): # draw state
            reduced_state[i] = num_states
            actual_state[num_states] = i
            num_states += 1

print(f"Number of valid states: {num_states}")

def build_transition_matrices(P,n=3):
    """ Build probability transition matrix for each action
    """
    # iterate for each action
    for u in range(9):
        for i in range(num_states):
            true_state_num = actual_state[i] # get the actual configuration of the state i
            true_state = num2state(true_state_num).flatten()
            numX = (true_state == 1).sum()
            numO = (true_state == 2).sum()
            if numO == numX:
                if check_losing(num2state(true_state_num)):
                    P[u][i][i] = 1.0
                    continue
                # print(f"True state: {true_state}")
                if true_state[u] == 0: # if the action is possible on this state
                    true_state[u] = 1
                    true_state = true_state.reshape((3,3))
                    if not check_winning(true_state):
                        true_state = true_state.flatten()
                        possibilities = (true_state == 0).sum() # count number of positions for O
                        if possibilities != 0:
                            for j in range(9):
                                if true_state[j] == 0:
                                    true_state[j] = 2
                                    true_state = true_state.reshape((3,3))
                                    new_state = state2num(true_state)
                                    true_state = true_state.flatten()
                                    # assign equal probability to each reachable state
                                    reachable_state = reduced_state[new_state]
                                    P[u][i][reachable_state] = 1.0 / possibilities
                                    true_state[j] = 0
                        else:
                            # no other state possible for draw state
                            new_state = state2num(true_state)
                            P[u][i][reduced_state[new_state]] = 1.0
                    else:
                        # no other state possible from winning state
                        new_state = state2num(true_state)
                        P[u][i][reduced_state[new_state]] = 1.0
            else:
                P[u][i][i] = 1.0 # absorbing states (actions do not have any effect)
                      
    return P

#create probability transition matrices for each the 9 actions
P = np.zeros((9,num_states,num_states))
P = build_transition_matrices(P)
absorbing_states = 0
for i in range(num_states):
    true_state = actual_state[i]
    board = num2state(true_state)
    if check_winning(board) or check_losing(board) or check_draw(board):
        absorbing_states += 1

print(f"Number of absorbing states: {absorbing_states}")

def arbitrary_policy(markers):
    for i in range(3):
        for j in range(3):
            if markers[i][j] == 0:
                return (i,j)
            
""" Function for calculating immediate reward
"""
def reward(cur_state_num,action):
    board = num2state(cur_state_num)
    total = 0
    board = board.flatten()
    board[action] = 1
    board = board.reshape((3,3))
    if check_winning(board):
        return 1.0
    if check_draw(board):
        return 0.0
    board = board.flatten()
    opponent_actions = get_actions(board)
    for op_ac in opponent_actions:
        board[op_ac] = 2
        board = board.reshape((3,3))
        new_state = reduced_state[state2num(board)]
        probability = P[action][reduced_state[cur_state_num]][new_state]
        if check_losing(board):
            total += probability * (-1.0)
        board = board.flatten()
        board[op_ac] = 0
    return total

""" get empty cells on the board or set of possible actions
"""
def get_actions(board):
    actions = []
    board = board.flatten()
    for i in range(9):
        if board[i] == 0:
            actions.append(i)
    return actions

def value_iteration():
    Vn = np.zeros((num_states,1)) # value function vector
    start = time.time()
    while True:
        V_next = np.zeros((num_states,1)) # value function for next iteration
        # go through all states
        for i in range(num_states):
            V_next[i][0] = -100000000
            # go through all the actions
            true_state_num = actual_state[i]
            cur_board_state = num2state(true_state_num)
            # no rewards or actions for winning, losing and draw states
            if check_winning(cur_board_state) or check_losing(cur_board_state) or check_draw(cur_board_state):
                V_next[i][0] = 0
                continue
            actions = get_actions(cur_board_state)
            cur_board_state = cur_board_state.flatten()
            for u in actions:
                immediate_reward = reward(true_state_num,u)
                cur_board_state[u] = 1
                next_value_fn = immediate_reward
                cur_board_state = cur_board_state.reshape((3,3))
                if not check_winning(cur_board_state):
                    cur_board_state = cur_board_state.flatten()
                    opponent_actions = get_actions(cur_board_state)
                    for op_ac in opponent_actions:
                        cur_board_state[op_ac] = 2
                        new_state = reduced_state[state2num(cur_board_state)]
                        next_value_fn += P[u][i][new_state] * Vn[new_state][0]
                        cur_board_state[op_ac] = 0
                else:
                    cur_board_state = cur_board_state.flatten()

                cur_board_state[u] = 0
                V_next[i][0] = max(V_next[i][0],next_value_fn)
        max_dif = 0
        for i in range(num_states):
            max_dif = max(max_dif,abs(V_next[i][0]-Vn[i][0]))
        if max_dif <= 0.01:
            break
        Vn = np.copy(V_next)
    

    end = time.time()
    print(f"Time taken: {end-start}")
    print("Optimal Value function computed")
    optimal_policy = [] 
    for i in range(num_states):
        max_value = -100000
        max_action = -1
        true_state_num = actual_state[i]
        cur_board_state = num2state(true_state_num)
        if check_winning(cur_board_state) or check_losing(cur_board_state) or check_draw(cur_board_state):
            optimal_policy.append(0)
            continue
        cur_board_state = cur_board_state.flatten()
        actions = get_actions(cur_board_state)
        for u in actions:
            immediate_reward = reward(true_state_num,u)
            total_reward = immediate_reward
            cur_board_state[u] = 1
            cur_board_state = cur_board_state.reshape((3,3))
            if not check_winning(cur_board_state):
                cur_board_state = cur_board_state.flatten()
                opponent_actions = get_actions(cur_board_state)
                for op_ac in opponent_actions:
                    cur_board_state[op_ac] = 2
                    new_state = reduced_state[state2num(cur_board_state)]
                    total_reward += P[u][i][new_state] * Vn[new_state][0]
                    cur_board_state[op_ac] = 0
            else:
                cur_board_state = cur_board_state.flatten()

            cur_board_state[u] = 0
            if max_value <= total_reward:
                max_value = total_reward
                max_action = u
        
        optimal_policy.append(max_action)
    return optimal_policy,Vn

value_policy,V = value_iteration()

def value_optimal_policy(policy,markers):
    board = np.array(markers)
    for i in range(3):
        for j in range(3):
            if board[i][j] == -1:
                board[i][j] = 2
    state_num = reduced_state[state2num(board)]
    optimal_action = policy[state_num]
    # print(board,optimal_action)
    return optimal_action

pygame.init()

screen_height = 300
screen_width = 300
line_width = 6
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Tic Tac Toe')

#define colours
red = (255, 0, 0)
green = (0, 255, 0)
blue = (0, 0, 255)

#define font
font = pygame.font.SysFont(None, 40)

#define variables
clicked = False
player = 1
pos = (0,0)
markers = []
game_over = False
winner = 0

#setup a rectangle for "Play Again" Option
again_rect = Rect(screen_width // 2 - 80, screen_height // 2, 160, 50)

#create empty 3 x 3 list to represent the grid
for x in range (3):
    row = [0] * 3
    markers.append(row)



def draw_board():
    bg = (255, 255, 210)
    grid = (50, 50, 50)
    screen.fill(bg)
    for x in range(1,3):
        pygame.draw.line(screen, grid, (0, 100 * x), (screen_width,100 * x), line_width)
        pygame.draw.line(screen, grid, (100 * x, 0), (100 * x, screen_height), line_width)

def draw_markers():
    x_pos = 0
    for x in markers:
        y_pos = 0
        for y in x:
            if y == 1:
                pygame.draw.line(screen, red, (x_pos * 100 + 15, y_pos * 100 + 15), (x_pos * 100 + 85, y_pos * 100 + 85), line_width)
                pygame.draw.line(screen, red, (x_pos * 100 + 85, y_pos * 100 + 15), (x_pos * 100 + 15, y_pos * 100 + 85), line_width)
            if y == -1:
                pygame.draw.circle(screen, green, (x_pos * 100 + 50, y_pos * 100 + 50), 38, line_width)
            y_pos += 1
        x_pos += 1    


def check_game_over():
    global game_over
    global winner

    x_pos = 0
    for x in markers:
        #check columns
        if sum(x) == 3:
            winner = 1
            game_over = True
        if sum(x) == -3:
            winner = 2
            game_over = True
        #check rows
        if markers[0][x_pos] + markers [1][x_pos] + markers [2][x_pos] == 3:
            winner = 1
            game_over = True
        if markers[0][x_pos] + markers [1][x_pos] + markers [2][x_pos] == -3:
            winner = 2
            game_over = True
        x_pos += 1

    #check cross
    if markers[0][0] + markers[1][1] + markers [2][2] == 3 or markers[2][0] + markers[1][1] + markers [0][2] == 3:
        winner = 1
        game_over = True
    if markers[0][0] + markers[1][1] + markers [2][2] == -3 or markers[2][0] + markers[1][1] + markers [0][2] == -3:
        winner = 2
        game_over = True

    #check for tie
    if game_over == False:
        tie = True
        for row in markers:
            for i in row:
                if i == 0:
                    tie = False
        #if it is a tie, then call game over and set winner to 0 (no one)
        if tie == True:
            game_over = True
            winner = 0



def draw_game_over(winner):

    if winner != 0:
        end_text = "Player " + str(winner) + " wins!"
    elif winner == 0:
        end_text = "You have tied!"

    end_img = font.render(end_text, True, blue)
    pygame.draw.rect(screen, green, (screen_width // 2 - 100, screen_height // 2 - 60, 200, 50))
    screen.blit(end_img, (screen_width // 2 - 100, screen_height // 2 - 50))

    again_text = 'Play Again?'
    again_img = font.render(again_text, True, blue)
    pygame.draw.rect(screen, green, again_rect)
    screen.blit(again_img, (screen_width // 2 - 80, screen_height // 2 + 10))


run = True
while run:

    #draw board and markers first
    draw_board()
    draw_markers()
    #handle events
    for event in pygame.event.get():
        #handle game exit
        if event.type == pygame.QUIT:
            run = False
        #run new game
        if game_over == False:
            # use optimal policy computed using value iteration
            action = value_optimal_policy(value_policy,markers)
            game_state = np.array(markers)
            game_state = np.where(game_state == -1,2,game_state)
            cur_state_num = state2num(game_state) # get the current state number
            cur_state_red = reduced_state[cur_state_num] # get the reduced state number for current state
            q = np.random.uniform()
            probability_sum = 0
            game_state = game_state.flatten()
            game_state[action] = 1
            game_state = game_state.reshape((3,3))
            if not check_winning(game_state):
                if not check_draw(game_state):
                    game_state = game_state.flatten()
                    opponent_actions = get_actions(game_state)
                    for op_ac in opponent_actions:
                        game_state[op_ac] = 2
                        next_state_red = reduced_state[state2num(game_state)]
                        probability_sum += P[action][cur_state_red][next_state_red]
                        # print(reduced_state[state_num])
                        if probability_sum >= q:
                            game_state = game_state.reshape((3,3))
                            break

                        game_state[op_ac] = 0
                

            for i in range(3):
                for j in range(3):
                    if game_state[i][j] == 2:
                        game_state[i][j] = -1
                    markers[i][j] = game_state[i][j]
            # markers[cell_x][cell_y] = player
            # player *= -1
            check_game_over()

    #check if game has been won
    if game_over == True:
        draw_game_over(winner)
        #check for mouseclick to see if we clicked on Play Again
        if event.type == pygame.MOUSEBUTTONDOWN and clicked == False:
            clicked = True
        if event.type == pygame.MOUSEBUTTONUP and clicked == True:
            clicked = False
            pos = pygame.mouse.get_pos()
            if again_rect.collidepoint(pos):
                #reset variables
                game_over = False
                player = 1
                pos = (0,0)
                markers = []
                winner = 0
                #create empty 3 x 3 list to represent the grid
                for x in range (3):
                    row = [0] * 3
                    markers.append(row)

    #update display
    pygame.display.update()

pygame.quit()