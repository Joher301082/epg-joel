#!/usr/bin/env python3
import unittest
from generate_epg import ambiguous_target_ids, choose_matches, score_candidate

def target(name, cid, group="USA"):
    return {"target_id":cid,"tvg_id":cid,"name":name,"display":name,"group":group}

def source(name,cid):
    return {"name":name,"norm":name.lower(),"base":name.lower(),
            "site":"example.com","site_id":"us#1","xmltv_id":cid,
            "file":"us.channels.xml","lang":"en","source_key":"src_test"}

class GeneratorSafetyTests(unittest.TestCase):
    def test_id_reused_for_distinct_channels_is_quarantined(self):
        rows=[target("FOX Sports","TIGO"),target("Tigo Sports","TIGO")]
        self.assertEqual(ambiguous_target_ids(rows),{"tigo"})
        chosen,unmatched=choose_matches(rows,[source("FOX Sports","TIGO")])
        self.assertEqual(len(chosen),0)
        self.assertEqual(len(unmatched),2)

    def test_quality_variants_do_not_trigger_false_alarm(self):
        rows=[target("HBO Plus HD","HBODA"),target("HBO Plus FHD","HBODA")]
        self.assertEqual(ambiguous_target_ids(rows),set())

    def test_country_variants_cannot_share_programming(self):
        rows=[target("HBO HD","HBO","COLOMBIA"),target("HBO FHD","HBO","MEXICO")]
        self.assertEqual(ambiguous_target_ids(rows),{"hbo"})

    def test_matching_id_but_wrong_name_is_rejected(self):
        self.assertLess(score_candidate(target("Disney Junior","La 1 HD"),
                        source("La 1","La 1 HD")),0)

    def test_matching_id_and_name_is_accepted(self):
        self.assertGreaterEqual(score_candidate(target("CNBC HD","CNBC"),
                                source("CNBC","CNBC")),350)

if __name__=="__main__":
    unittest.main()
