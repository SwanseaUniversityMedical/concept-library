import random

def generate_dag(connectivity=0.5, min_rank_width=2, max_rank_width=4, min_rank_height=3, max_rank_height=5):
    ranks = random.randint(min_rank_height, max_rank_height)
    nodes = 0
    node_counter = 0
    network = []
    rank_list = []

    for i in range(ranks):
        new_nodes = random.randint(min_rank_width, max_rank_width)

        ranks = []
        for j in range(new_nodes):
            ranks.append(node_counter)
            node_counter += 1
        rank_list.append(ranks)

        if i > 0:
            for j in rank_list[i - 1]:
                for k in range(new_nodes):
                    if random.random() < connectivity:
                        network.append((j, k+nodes))

        nodes += new_nodes

    return network

def generate_tree(size=10):
    sequence = [random.choice(range(size)) for i in range(size - 2)]
    height = len(sequence)
    L = set(range(height+2))
    network = []

    for i in range(height):
        u, v = sequence[0], min(L - set(sequence))
        sequence.pop(0)
        L.remove(v)
        network.append((u,v))
    network.append((L.pop(), L.pop()))

    return network
