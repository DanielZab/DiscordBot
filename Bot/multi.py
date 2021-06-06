import multiprocessing as mp


def start_process(target, args):
    '''
    Starts a multiprocess
    '''
    process = mp.Process(target=target, args=args)
    process.start()
    process.join()
