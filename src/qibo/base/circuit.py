# -*- coding: utf-8 -*-
# @authors: S. Carrazza and A. Garcia
from abc import ABCMeta, abstractmethod
from typing import Tuple


class BaseCircuit(object):
    """Circuit object which holds a list of gates.

    This circuit is symbolic and cannot perform calculations.
    A specific backend (eg. Tensorflow) has to be used for performing
    calculations (evolving the state vector).
    All backend-based circuits should inherit `BaseCircuit`.

    Args:
        nqubits (int): Total number of qubits in the circuit.

    Example:
        ::

            from qibo.models import Circuit
            from qibo import gates
            c = Circuit(3) # initialized circuit with 3 qubits
            c.add(gates.H(0)) # added Hadamard gate on qubit 0
    """

    __metaclass__ = ABCMeta

    def __init__(self, nqubits):
        self.nqubits = nqubits
        self.queue = []
        # Flag to keep track if the circuit was executed
        # We do not allow adding gates in an executed circuit
        self.is_executed = False

        self.measurement_sets = dict()
        self.measurement_gate = None
        self.measurement_gate_result = None

    def __add__(self, circuit):
        """Add circuits.

        Args:
            circuit: Circuit to be added to the current one.

        Returns:
            The resulting circuit from the addition.
        """
        return BaseCircuit._circuit_addition(self, circuit)

    @classmethod
    def _circuit_addition(cls, c1, c2):
        if c1.nqubits != c2.nqubits:
            raise ValueError("Cannot add circuits with different number of "
                             "qubits. The first has {} qubits while the "
                             "second has {}".format(c1.nqubits, c2.nqubits))
        newcircuit = cls(c1.nqubits)
        for gate in c1.queue:
            newcircuit.add(gate)
        for gate in c2.queue:
            newcircuit.add(gate)
        return newcircuit

    def _check_measured(self, gate_qubits: Tuple[int]):
        """Helper method for `add`.

        Checks if the qubits that a gate acts are already measured and raises
        a `NotImplementedError` if they are because currently we do not allow
        measured qubits to be reused.
        """
        for qubit in gate_qubits:
            if (self.measurement_gate is not None and
                qubit in self.measurement_gate.target_qubits):
                raise ValueError("Cannot reuse qubit {} because it is already "
                                 "measured".format(qubit))

    def add(self, gate):
        """Add a gate to a given queue.

        Args:
            gate (:class:`qibo.base.gates.Gate`): the gate object to add.
                See :ref:`Gates` for a list of available gates.
        """
        if self._final_state is not None:
            raise RuntimeError("Cannot add gates to a circuit after it is "
                               "executed.")

        # Set number of qubits in gate
        if gate._nqubits is None:
            gate.nqubits = self.nqubits
        elif gate.nqubits != self.nqubits:
            raise ValueError("Attempting to add gate with {} total qubits to "
                             "a circuit with {} qubits."
                             "".format(gate.nqubits, self.nqubits))

        self._check_measured(gate.qubits)
        if gate.name == "measure":
            self._add_measurement(gate)
        else:
            self.queue.append(gate)

    def _add_measurement(self, gate):
        """Gets called automatically by `add` when `gate` is measurement.

        This is because measurement gates (`gates.M`) are treated differently
        than all other gates.
        The user is not supposed to use the `add_measurement` method.
        """
        # Set register's name and log the set of qubits in `self.measurement_sets`
        name = gate.register_name
        if name is None:
            name = "Register{}".format(len(self.measurement_sets))
            gate.register_name = name
        elif name in self.measurement_sets:
            raise KeyError("Register name {} has already been used."
                           "".format(name))

        # Update circuit's global measurement gate
        if self.measurement_gate is None:
            self.measurement_gate = gate
            self.measurement_sets[name] = set(gate.target_qubits)
        else:
            self.measurement_gate._add(gate.target_qubits)
            self.measurement_sets[name] = gate.target_qubits

    @property
    def size(self) -> int:
        """Total number of qubits in the circuit."""
        return self.nqubits

    @property
    def depth(self) -> int:
        """Total number of gates/operations in the circuit."""
        return len(self.queue)

    @abstractmethod
    def execute(self):
        """Executes the circuit. Exact implementation depends on the backend."""
        raise NotImplementedError

    def to_qasm(self):
        """Convert circuit to QASM.

        Args:
            filename (str): The filename where the code is saved.
        """
        code = ["# Generated by QIBO"]
        code += ["OPENQASM 2.0;"]
        code += ["include \"qelib1.inc\";"]
        code += [f"qreg q[{self.nqubits}];"]
        is_measure = False
        for item in self.queue:
            gate, ids = item.gate2qasm()
            if gate == 'MX':
                code += f"h q[{ids[0]}];\n"
                code += f"measure q[{idx[0]}] -> c[0];\n"
                is_measure = True
            elif gate == 'MY':
                code += f"swap q[{ids[0]}], q[{ids[1]}];\n"
                code += f"h q[{ids[0]}];\n"
                code += f"measure q[{idx[0]}] -> c[0];\n"
                is_measure = True
            elif gate == 'measure':
                code += f"measure q[{ids[0]}] -> c[0];\n"
                is_measure = True
            else:
                data = f"{gate} q[{ids[0]}]"
                if len(ids) > 1:
                    data  += f", q[{ids[1]}]"
                data  += ";"
                code += [data]
        if is_measure:
            code.insert(4, "creg c[1];")
        return "\n".join(code)
