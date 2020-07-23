import tensorflow as tf
from tensorflow.python.framework import ops


@ops.RegisterGradient("InitialState")
def _initial_state_grad(op, grad):
    """The gradients for `initial_state`.

    Args:
        op: The `initial_state` `Operation` that we are differentiating, which we can use
        to find the inputs and outputs of the original op.
        grad: Gradient with respect to the output of the `initial_state` op.

    Returns:
        Gradients with respect to the input of `initial_state`.
    """
    to_initial_state = tf.concat([[0], grad[1:]], axis=0)
    return [to_initial_state]