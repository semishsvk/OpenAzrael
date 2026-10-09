from __future__ import annotations
import unittest
import numpy as np
from tools.remaster_framework.gltf_raw import node_local_matrix

class RawGltfTests(unittest.TestCase):
    def test_column_major_matrix(self):
        # glTF translation in a column-major matrix.
        flat=[1,0,0,0, 0,1,0,0, 0,0,1,0, 3,4,5,1]
        m=node_local_matrix({"matrix":flat})
        np.testing.assert_allclose(m[:3,3],[3,4,5])

    def test_trs_translation(self):
        m=node_local_matrix({"translation":[1,2,3]})
        np.testing.assert_allclose(m[:3,3],[1,2,3])

if __name__=="__main__":
    unittest.main()
