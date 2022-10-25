# by Stefan Vocht
#
# this script is used to learn a MHN using state space restriction or the approximated gradient
#

import numpy as np
from scipy.optimize import minimize, OptimizeResult

from typing import Callable

from .state_storage import State_storage, create_indep_model
from . import state_space_restriction
from . import approximate_gradient as ag


def L1(theta: np.ndarray, eps: float = 1e-05) -> float:
    """
    Computes the L1 penalty
    """
    theta_ = theta.copy()
    np.fill_diagonal(theta_, 0)
    return np.sum(np.sqrt(theta_**2 + eps))


def L1_(theta: np.ndarray, eps: float = 1e-05) -> np.ndarray:
    """
    Derivative of the L1 penalty
    """
    theta_ = theta.copy()
    np.fill_diagonal(theta_, 0)
    return theta_ / np.sqrt(theta_**2 + eps)


def reg_state_space_restriction_score(theta: np.ndarray, states: State_storage, lam: float,
                                      n: int, score_grad_container: list) -> float:
    """
    Computes the score using state space restriction with L1 regularization

    :param theta: current theta
    :param states: states observed in the data
    :param lam: regularization parameter
    :param n: size of theta (nxn)
    :param score_grad_container: a list that enables this function to communicate with the gradient function
    :return: regularized score
    """
    theta = theta.reshape((n, n))

    # grad, score = state_space_restriction.gradient_and_score(theta, states)
    print("Start computing gradient")
    grad, score = state_space_restriction.gradient_and_score(theta, states)
    print("Finish")
    score_grad_container[0] = grad

    return -(score - lam * L1(theta))


def reg_state_space_restriction_gradient(theta: np.ndarray, states: State_storage, lam: float,
                                         n: int, score_grad_container: list) -> np.ndarray:
    """
    Computes the gradient state space restriction with L1 regularization

    :param theta: current theta
    :param states: states observed i the data
    :param lam: regularization parameter
    :param n: size of theta (nxn)
    :param score_grad_container: a list that enables this function to communicate with the score function
    :return: regularized gradient
    """

    n = n or int(np.sqrt(theta.size))
    theta_ = theta.reshape((n, n))

    grad = score_grad_container[0]
    if grad is None:
        grad, score = state_space_restriction.gradient(theta, states)

    return -(grad - lam * L1_(theta_)).flatten()


def reg_approximate_score(theta: np.ndarray, states: State_storage, lam: float,
                                      n: int, score_grad_container: list) -> float:
    """
    Computes the score using the approximate score with L1 regularization

    :param theta: current theta
    :param states: states observed in the data
    :param lam: regularization parameter
    :param n: size of theta (nxn)
    :param score_grad_container: a list that enables this function to communicate with the gradient function
    :return: regularized score
    """
    theta = theta.reshape((n, n))

    # grad, score = state_space_restriction.gradient_and_score(theta, states)
    print("Start approximating gradient")
    grad, score = ag.gradient_and_score_using_c(np.exp(theta), states, 50, 10)
    print("Finish")
    score_grad_container[0] = grad

    return -(score - lam * L1(theta))


def reg_approximate_gradient(theta: np.ndarray, states: State_storage, lam: float,
                                         n: int, score_grad_container: list) -> np.ndarray:
    """
    Computes the gradient state space restriction with L1 regularization

    :param theta: current theta
    :param states: states observed i the data
    :param lam: regularization parameter
    :param n: size of theta (nxn)
    :param score_grad_container: a list that enables this function to communicate with the score function
    :return: regularized gradient
    """

    n = n or int(np.sqrt(theta.size))
    theta_ = theta.reshape((n, n))

    grad = score_grad_container[0]
    if grad is None:
        grad, score = ag.gradient_and_score_using_c(np.exp(theta), states, 50, 10)

    return -(grad - lam * L1_(theta_)).flatten()


def learn_MHN(states: State_storage, init: np.ndarray = None, lam: float = 0, maxit: int = 5000,
              trace: bool = False, reltol: float = 1e-07, round_result: bool = True, callback: Callable = None,
              score_func: Callable = reg_state_space_restriction_score,
              jacobi: Callable = reg_state_space_restriction_gradient) -> OptimizeResult:
    """
    This function is used to train a MHN, it is very similar to the learn_MHN function from the original MHN

    :param states: a State_storage object containing all mutation states observed in the data
    :param init: starting point for the training (initial theta)
    :param lam: tuning parameter for regularization
    :param maxit: maximum number of training iterations
    :param trace: set to True to print convergence messages (see scipy.optimize.minimize)
    :param reltol: Gradient norm must be less than reltol before successful termination (see "gtol" scipy.optimize.minimize)
    :param round_result: if True, the result is rounded to two decimal places
    :param callback: function called after each iteration, must take theta as argument
    :param score_func: score function used for training
    :param jacobi: gradient function used for training
    :return: trained model
    """

    n = states.get_data_shape()[1]

    if init is None:
        init = create_indep_model(states)

    # this container is given to the score and gradient function to communicate with each other
    score_and_gradient_container = [None, None]

    opt = minimize(fun=score_func, x0=init, args=(states, lam, n, score_and_gradient_container), method="L-BFGS-B",
                   jac=jacobi, options={'maxiter': maxit, 'disp': trace, 'gtol': reltol}, callback=callback)

    opt.x = opt.x.reshape((n, n))

    if round_result:
        opt.x = np.around(opt.x, decimals=2)

    return opt
