import numpy as np
import torch
import time


torch.set_printoptions(precision=16)
np.set_printoptions(precision=16)


class CompetitiveSolver(object):
    def __init__(self, device="cpu", max_iter=10, tol=1e-3):
        self.device = device
        self.max_iter = max_iter
        self.tol = tol


    def np_solve(self, AT: np.ndarray, BT: np.ndarray, K:np.ndarray):
        # 求解
        nA = len(AT)
        nB = len(BT)
        AF = np.zeros(AT.shape, dtype=np.float32)
        BF = np.zeros(BT.shape, dtype=np.float32)

        err = 0
        for iter in range(self.max_iter):
            AF_last = AF
            BF_last = BF
            AF = AT / ((K * BF.reshape(1, nB)).sum(axis=1) + 1)
            BF = BT / ((K * AF.reshape(nA, 1)).sum(axis=0) + 1)
            # print('iter', iter, AF, BF)
            err = np.abs(AF-AF_last).sum() + np.abs(BF-BF_last).sum()
            if (err < self.tol):
                break
        if (err > self.tol):
            print(f'not converge in {self.max_iter} iterations')
        C = K * AF.reshape(nA, 1) * BF.reshape(1, nB)

        return AF, BF, C


    '''def np_gradient(self, AF, BF, K, p, q):
        # 求解dCij/dKpq
        # 先求解dAF/dKpq, dBF/dKpq, nA+nB维线性方程组
        nA = len(AF)
        nB = len(BF)
        # 一行一行填W
        W = np.zeros((nA+nB, nA+nB))
        for m in range(nA):
            # 第m行
            for j in range(nB):
                # 第nA+j列
                W[m, nA+j] += K[m, j] * AF[m]
                # 第m列
                W[m, m] += K[m, j] * BF[j]
            W[m, m] += 1
        for n in range(nB):
            # 第nA+n行
            for i in range(nA):
                # 第i列
                W[nA+n, i] += K[i, n] * BF[n]
                # 第nA+n列
                W[nA+n, nA+n] += K[i, n] * AF[i]
            W[nA+n, nA+n] += 1

        b = np.zeros((nA+nB, 1))
        b[p, 0] += - AF[p] * BF[q]
        b[nA+q, 0] += - AF[p] * BF[q]
        
        dAdB = np.linalg.solve(W, b)
        dA = dAdB[:nA]
        dB = dAdB[nA:]

        # 然后求dC/pKpq
        dC = np.zeros((nA, nB))
        for i in range(nA):
            for j in range(nB):
                dC[i, j] += K[i, j] * BF[j] * dA[i] + K[i, j] * AF[i] * dB[j]
        dC[p, q] += AF[p] * BF[q]

        return dC'''


    def np_gradient_all(self, AF, BF, K):
        
        # 一次性求解dCij/dKpq
        nA = len(AF)
        nB = len(BF)
        dC_dK = np.zeros((nA, nB, nA, nB), dtype=np.float32)
        dA_dK = np.zeros((nA, nA, nB), dtype=np.float32)
        dB_dK = np.zeros((nB, nA, nB), dtype=np.float32)
        
        
        # 先求解dAF/dKpq, dBF/dKpq, nA+nB维线性方程组
        W = np.zeros((nA+nB, nA+nB), dtype=np.float32)
        # 一行一行填W
        for m in range(nA):
            # 第m行
            for j in range(nB):
                # 第nA+j列
                W[m, nA+j] += K[m, j] * AF[m]
                # 第m列
                W[m, m] += K[m, j] * BF[j]
            W[m, m] += 1
        for n in range(nB):
            # 第nA+n行
            for i in range(nA):
                # 第i列
                W[nA+n, i] += K[i, n] * BF[n]
                # 第nA+n列
                W[nA+n, nA+n] += K[i, n] * AF[i]
            W[nA+n, nA+n] += 1

        W_inv = np.linalg.inv(W)
        
        # t0 = time.perf_counter()
        # for i in range(1000):
        #     W_inv = np.linalg.inv(W)
        # t1 = time.perf_counter()
        # print('process time', t1-t0)


        # 对于给定的Kpq
        for p in range(nA):
            for q in range(nB):
                b = np.zeros((nA+nB, 1))
                b[p, 0] += - AF[p] * BF[q]
                b[nA+q, 0] += - AF[p] * BF[q]
                x = np.matmul(W_inv, b).reshape(-1)
                dA_dK[:, p, q] = x[:nA]
                dB_dK[:, p, q] = x[nA:]

        # 然后求dC/pKpq
        for i in range(nA):
            for j in range(nB):
                dC_dK[i, j] += K[i, j] * BF[j] * dA_dK[i] + K[i, j] * AF[i] * dB_dK[j]
                dC_dK[i, j, i, j] += AF[i] * BF[j]

        return dC_dK


    def torch_solve(self, AT, BT, K):
        # 求解
        nA = len(AT)
        nB = len(BT)
        AF = torch.zeros(AT.shape)
        BF = torch.zeros(BT.shape)

        err = 0
        for iter in range(self.max_iter):
            AF_last = AF
            BF_last = BF
            AF = AT / ((K * BF.reshape(1, nB)).sum(axis=1) + 1)
            BF = BT / ((K * AF.reshape(nA, 1)).sum(axis=0) + 1)
            # print('iter', iter, AF, BF)
            err = np.abs(AF-AF_last).sum() + np.abs(BF-BF_last).sum()
            if (err < self.tol):
                break
        if (err > self.tol):
            print(f'not converge in {iter} iterations')
        C = K * AF.reshape(nA, 1) * BF.reshape(1, nB)

        return AF, BF, C


    def torch_iterate_once(self, AT, BT, K, AF, BF, C):
        # pytorch 自动求导最后一步迭代
        nA = len(AF)
        nB = len(BF)
        AF_last = AF
        BF_last = BF
        # simultaneous iteration
        AF = AT / ((K * BF_last.reshape(1, nB)).sum(axis=1) + 1)
        BF = BT / ((K * AF_last.reshape(nA, 1)).sum(axis=0) + 1)
        # or alternative iteration
        # AF = AT / ((K * BF).sum(axis=1, keepdims=True) + 1)
        # BF = BT / ((K * AF).sum(axis=0, keepdims=True) + 1)
        C = K * AF.reshape(nA, 1) * BF.reshape(1, nB)

        return AF, BF, C



if __name__ == '__main__':

    # 2v2 competition
    '''AT = np.array([1., 1.])
    BT = np.array([1., 1., 1.])
    K  = np.array([1., 2., 3., 4., 5., 6.]).reshape(2, 3)
    AF, BF, C = CompetitiveSolver.np_solve(AT, BT, K)
    print('AT, BT, K')
    print(AT, BT, K)
    print('AF, BF, C')
    print(AF, BF, C)

    # numerical simulation
    for dK00 in [1e-4]:
        AT_ = AT
        BT_ = BT
        K_ = K.copy()
        K_[0, 0] = K[0, 0]+ dK00
        # print('K = ', K_)
        AF_, BF_, C_ = CompetitiveSolver.np_solve(AT_, BT_, K_)

        # print(AF_, BF_, C_)
        dC1 = (C_ - C) / dK00
    print('numerical dC/pK00')
    print(dC1)

    # theoretical
    dC3 = CompetitiveSolver.np_gradient(AF, BF, K, p=0, q=0)
    print('analytical dC/pK00')
    print(dC3)
    

    dC_dK = CompetitiveSolver.np_gradient_all(AF, BF, K)
    print('dC/dK')
    print(dC_dK)
    print('dC/pK00')
    print(dC_dK[:, :, 0, 0])'''


    
    '''AF, BF, C = CompetitiveSolver.torch_iterate_once(AT, BT, K, AF, BF, C)
    C[0, 0].backward(retain_graph=True)
    print('last iter grad (simultaneous) dC00/pK')
    print(K.grad)'''



    solver = CompetitiveSolver(device="cpu", max_iter=20, tol=1e-3)

    # torch autograd
    AT = torch.Tensor([1, 1])
    BT = torch.Tensor([1, 1, 1])
    K  = torch.Tensor([1, 2, 3, 4, 5, 6]).reshape(2,3)
    K.requires_grad = True


    t0 = time.perf_counter()
    for i in range(1000):
        with torch.no_grad():
            AF, BF, C = solver.torch_solve(AT, BT, K)
    t1 = time.perf_counter()
    print('torch_solve time', t1-t0)


    AT, BT, K = AT.numpy(), BT.numpy(), K.detach().numpy()

    t0 = time.perf_counter()
    for i in range(1000):
        AF, BF, C = solver.np_solve(AT, BT, K)
    t1 = time.perf_counter()
    print('np_solve time', t1-t0)


    t0 = time.perf_counter()
    for i in range(1000):
        dC_dK = solver.np_gradient_all(AF, BF, K)
    t1 = time.perf_counter()
    print('np_gradient_all time', t1-t0)


'''
torch_solve time 0.82
np_solve time 0.17
np_gradient_all time 0.092
'''