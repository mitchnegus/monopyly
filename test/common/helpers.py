"""Common helper objects to improve modularity of tests."""
from monopyly.database.models import TransactionTag

from ..helpers import TestHandler


class TestTagHandler(TestHandler):
    # References only include entries accessible to the authorized login
    db_reference = [
        TransactionTag(id=2, user_id=3, parent_id=None, tag_name="Transportation"),
        TransactionTag(id=3, user_id=3, parent_id=2, tag_name="Parking"),
        TransactionTag(id=4, user_id=3, parent_id=2, tag_name="Railroad"),
        TransactionTag(id=5, user_id=3, parent_id=None, tag_name="Utilities"),
        TransactionTag(id=6, user_id=3, parent_id=5, tag_name="Electricity"),
        TransactionTag(id=7, user_id=3, parent_id=None, tag_name="Credit payments"),
        TransactionTag(id=8, user_id=3, parent_id=None, tag_name="Gifts"),
    ]

    db_reference_hierarchy = {
        db_reference[0]: {
            db_reference[1]: {},
            db_reference[2]: {},
        },
        db_reference[3]: {
            db_reference[4]: {},
        },
        db_reference[5]: {},
        db_reference[6]: {},
    }

    def _compare_hierarchies(self, hierarchy, reference_hierarchy):
        self.assertEntriesMatch(hierarchy.keys(), reference_hierarchy.keys())
        # Double loop over heirarchies to test equivalence regardless of order
        for key, subhierarchy in hierarchy.items():
            for ref_key, ref_subhierarchy in reference_hierarchy.items():
                if key.id == ref_key.id:
                    self._compare_hierarchies(subhierarchy, ref_subhierarchy)
