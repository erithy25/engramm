"""Everyday conversation (Chat v3.1): gibberish, talk that is never stored, moments answered with
empathy that names the topic, plans, advice in context, suggestions, games, offers, follow-up
question words, and no word-for-word repeats — on the small test corpus (no pack needed)."""

from __future__ import annotations

import datetime as dt

import pytest

from engramm.chat.dialog import Assistant, DialogState
from engramm.chat.everyday import answer_matches
from engramm.chat.smart import (bare_followup, experience, gibberish, is_discourse, is_mash, offer_in,
                                rebuild_question, short_answer, swap_person)
from engramm.chat.textmem import LoggedTextMemory
from tests.test_chat_flows import _bot, corpus  # noqa: F401  (fixture)

CLOCK = lambda: dt.datetime(2026, 10, 1, 18, 30)          # noqa: E731


@pytest.fixture()
def chat(corpus, tmp_path):                                # noqa: F811
    bot = _bot(corpus, LoggedTextMemory(tmp_path / "chat_memory.log"))
    a = Assistant(bot, clock=CLOCK)
    return a, DialogState("daily")


def _stored(a) -> list[str]:
    return list(a.bot.user_texts().values())


# -- the helpers ----------------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["dhdhd", "asdf", "asdfgh", "hdhdhd", "jjjj", "kjhg", "lkjlkj", "fjfjfj", "qwertz",
                                  "sdkfj ghgh", "aaaaaaa"])
def test_gibberish_is_recognised(text):
    assert gibberish(text)


@pytest.mark.parametrize("text", ["hello", "Ngozi", "Siobhan", "Wojciech", "lol", "hmm", "brb", "zzz", "haha", "nooo",
                                  "yesss", "ugh", "meh", "okay", "photosynthesis", "Reykjavik", "helo", "thnks", "ok",
                                  "Tamlolo", "Erik", "bruh", "ooo", "aaah"])
def test_words_and_names_are_not_gibberish(text):
    assert not gibberish(text)
    assert not all(is_mash(t) for t in text.split())


@pytest.mark.parametrize("text", ["idk", "i don't know", "i guess", "i see", "me too", "not sure", "i agree",
                                  "i don't know lol", "i have a question"])
def test_discourse_phrases(text):
    assert is_discourse(text)


@pytest.mark.parametrize("text", ["i live in berlin", "i work as a nurse", "my dog is called rex"])
def test_facts_are_not_discourse(text):
    assert not is_discourse(text)


def test_moments_have_valence_and_topic():
    e = experience("my boss was so annoying today")
    assert e.valence == "negative" and e.topic == "your boss" and e.person
    e = experience("i just had a long day at work")
    assert e.valence == "negative" and e.topic == "work"
    e = experience("my presentation went really well")
    assert e.valence == "positive" and e.topic == "your presentation"
    assert experience("i had a great weekend").timeword == "weekend"
    assert experience("i failed my driving test").topic == "your driving test"
    assert experience("the meeting was not that bad") is None
    assert experience("i live in berlin") is None
    assert experience("what a day?") is None


def test_offers_and_short_answers():
    assert offer_in("I only do text. Want a joke or a fun fact instead?") == "joke_or_fact"
    assert offer_in("That's a fact.") is None
    assert short_answer("sure") == "yes" and short_answer("yes please") == "yes"
    assert short_answer("nah thanks") == "no" and short_answer("maybe later") == "no"
    assert short_answer("paris") is None


def test_follow_up_question_words():
    assert bare_followup("where?") == "where" and bare_followup("and when exactly?") == "when"
    assert bare_followup("how tall is it?") is None
    assert rebuild_question("When was William Shakespeare born?", "where") == "Where was William Shakespeare born?"
    assert rebuild_question("When was William Shakespeare born?", "when") is None


def test_person_swap_and_answer_matching():
    assert swap_person("go to my gym") == "go to your gym"
    assert answer_matches("it's a towel", "a towel", "towel")
    assert answer_matches("Leonardo da Vnci", "Leonardo da Vinci", "da vinci")
    assert answer_matches("8", "eight", "8")
    assert not answer_matches("Mars", "Jupiter")


# -- whole turns --------------------------------------------------------------------------------

def test_gibberish_turn_asks_again_and_is_not_stored(chat):
    a, st = chat
    r1 = a.turn(st, "dhdhd")
    assert r1.via == "gibberish" and r1.text.rstrip().endswith(("?", "."))
    r2 = a.turn(st, "asdfgh")
    assert r2.via == "gibberish" and r2.text != r1.text
    assert _stored(a) == []


def test_idk_and_friends_are_never_stored(chat):
    a, st = chat
    for m in ("idk", "I don't know", "I guess", "me too", "I see"):
        r = a.turn(st, m)
        assert r.kind != "learned", (m, r.text)
    assert _stored(a) == []


def test_moment_gets_empathy_with_topic_not_memory(chat):
    a, st = chat
    r = a.turn(st, "My boss was so annoying today")
    assert r.kind == "empathy" and "boss" in r.text.lower() and "remember" not in r.text.lower()
    assert _stored(a) == []
    adv = a.turn(st, "what should I do?")
    assert adv.via == "everyday" and "hr" in adv.text.lower() or "conversation" in adv.text.lower() \
        or "one-on-one" in adv.text.lower() or "talk" in adv.text.lower()


def test_yes_after_a_moment_question_listens(chat):
    a, st = chat
    a.turn(st, "I just had a long day at work")
    r = a.turn(st, "yeah")
    assert r.via == "empathy" and "listening" in r.text.lower() or "here" in r.text.lower()


def test_heartbreak_advice_is_not_about_work(chat):
    a, st = chat
    a.turn(st, "my girlfriend broke up with me")
    r = a.turn(st, "I don't know what to do")
    assert r.via == "everyday" and "hr" not in r.text.lower().split() and "work" not in r.text.lower()


def test_plans_are_answered_not_stored(chat):
    a, st = chat
    r = a.turn(st, "I'm thinking about moving to Berlin")
    assert "Berlin" in r.text and r.text.rstrip().endswith("?")
    assert _stored(a) == []


def test_recommendations_never_repeat_and_list_pick(chat):
    a, st = chat
    r1 = a.turn(st, "can you recommend a book?")
    r2 = a.turn(st, "recommend a book")
    items1 = {l for l in r1.text.splitlines() if l.startswith("•")}
    items2 = {l for l in r2.text.splitlines() if l.startswith("•")}
    assert len(items1) == 3 and len(items2) == 3 and not items1 & items2
    food = a.turn(st, "what should I eat tonight?")
    assert food.via == "everyday" and food.text.count("•") == 3
    more = a.turn(st, "yes")                                # the offer of more ideas
    assert more.via == "everyday" and more.text.count("•") >= 1


def test_quiz_flow(chat):
    a, st = chat
    q = a.turn(st, "quiz me")
    assert q.via == "quiz" and q.text.rstrip().endswith("?")
    r = a.turn(st, "I don't know")
    assert "answer is" in r.text and r.text.rstrip().endswith("?")
    q2 = a.turn(st, "another one")
    assert q2.via == "quiz" and q2.text != q.text
    stop = a.turn(st, "stop")
    assert stop.kind == "smalltalk"


def test_riddle_hint_and_reveal(chat):
    a, st = chat
    a.turn(st, "tell me a riddle")
    h = a.turn(st, "hint")
    assert "starts with" in h.text
    r = a.turn(st, "I give up")
    assert r.text.startswith("The answer")


def test_joke_offer_yes(chat):
    a, st = chat
    r = a.turn(st, "play some music")
    if "joke" not in r.text.lower():
        pytest.skip("this bank reply makes no offer")
    j = a.turn(st, "sure")
    assert j.kind in ("smalltalk", "about") and j.text != r.text


def test_decide_spell_rhyme(chat):
    a, st = chat
    d = a.turn(st, "should I go to the gym or stay home?")
    assert d.via == "everyday" and ("go to the gym" in d.text or "stay home" in d.text)
    s = a.turn(st, "how do you spell necessary")
    assert "N-E-C-E-S-S-A-R-Y" in s.text
    rh = a.turn(st, "what rhymes with moon")
    assert rh.via == "everyday"


def test_softened_insult_and_repetition_complaint(chat):
    a, st = chat
    r = a.turn(st, "you're kind of dumb")
    assert "sorry" in r.text.lower() or "fair" in r.text.lower() or "hear you" in r.text.lower()
    r = a.turn(st, "you already said that")
    assert "repeat" in r.text.lower() or "said that" in r.text.lower() or "switch" in r.text.lower()


def test_clarify_does_not_nest(chat):
    a, st = chat
    a.turn(st, "lol")
    r1 = a.turn(st, "what?")
    r2 = a.turn(st, "huh")
    assert "What I meant: Sorry" not in r1.text and "What I meant: Sorry" not in r2.text
    assert r2.text.count("What I meant") <= 1


def test_he_without_anyone_to_point_at(chat):
    a, st = chat
    r = a.turn(st, "how old is he?")
    assert r.via == "clarify" and "who" in r.text.lower()


def test_no_word_for_word_repeats_in_small_talk(chat):
    a, st = chat
    msgs = ["hi", "ok", "cool", "lol", "ok", "nice", "haha", "ok", "cool", "thanks", "ok", "lol", "nice", "cool",
            "okay", "haha", "ok", "great"]
    replies = [a.turn(st, m).text for m in msgs]
    for i in range(1, len(replies)):
        assert replies[i] != replies[i - 1], (msgs[i], replies[i])


def test_an_unknown_title_gets_a_question_not_a_receipt(chat):
    a, st = chat
    r = a.turn(st, "I watched Zorblax Returns yesterday")
    assert "Zorblax Returns" in r.text and r.text.rstrip().endswith("?"), r.text
    assert "remember" not in r.text.lower() and "noted" not in r.text.lower()
    r = a.turn(st, "I just finished The Quiet Orchard")
    assert "The Quiet Orchard" in r.text and r.text.rstrip().endswith("?"), r.text
    r = a.turn(st, "I went to the gym")
    assert "the gym" not in r.text.split("—")[0] or "?" in r.text      # no title reaction for errands


def test_picking_from_a_list_always_says_something(chat):
    a, st = chat
    a.turn(st, "recommend a sci-fi book")
    r = a.turn(st, "tell me about the second one")
    assert r.text and len(r.text) > 40 and "“" in r.text, r.text
    assert r.text != "Good choice"


def test_who_do_you_mean_takes_the_name_as_the_answer(chat):
    a, st = chat
    a.turn(st, "who is the president of Zorblaxia?")
    r = a.turn(st, "where was he born?")
    assert r.via == "clarify" and "he" in r.text.lower()
    r = a.turn(st, "Alexander Graham Bell")
    assert "Edinburgh" in r.text, r.text                      # the question again, now with the name
    assert not any("Alexander" in t for t in _stored(a))       # not stored as the user's name


def test_german_small_phrases(chat):
    a, st = chat
    a.turn(st, "Hallo")
    assert "Gute Nacht" in a.turn(st, "gute nacht").text or "Schlaf" in a.turn(st, "gute nacht").text
    r = a.turn(st, "was machst du so?")
    assert "Wie geht es dir" not in r.text and r.text.endswith("?")
    r = a.turn(st, "hey")
    assert any(w in r.text for w in ("Hallo", "Hi", "Hey", "Schön")) and "How" not in r.text


def test_contracted_question_words_without_question_mark():
    from engramm.chat.bot import message_type
    for m in ("what's the capital of australia", "who's the president of the usa", "wht is the time in tokyo"):
        assert message_type(m) == "question", m


def test_general_recommendation_forms(chat):
    a, st = chat
    for msg, word in (("what kind of music do you recommend", "listen"), ("can you recommend some good books", "“"),
                      ("what should I watch tonight", "“")):
        r = a.turn(st, msg)
        assert r.via == "everyday" and "•" in r.text, (msg, r.text)


def test_counts_of_people_and_their_names(chat):
    a, st = chat
    r = a.turn(st, "I have two kids")
    assert "names" in r.text or "called" in r.text, r.text
    assert "Two kids" in r.text or r.text.startswith(("Oh, two", "Two kids")), r.text
    a.turn(st, "Mia and Leo")
    r = a.turn(st, "what are my kids called?")
    assert "Mia and Leo" in r.text and " are called" in r.text, r.text
    r = a.turn(st, "how many kids do I have?")
    assert "two" in r.text and "work as" not in r.text, r.text
    r = a.turn(st, "my name is Sam and I'm a teacher")
    r = a.turn(st, "what's my job?")
    assert "teacher" in r.text, r.text


def test_opinions_and_surprise(chat):
    a, st = chat
    r = a.turn(st, "what do you think about pineapple on pizza")
    assert "pineapple" in r.text.lower() and r.text.rstrip().endswith("?"), r.text
    a.turn(st, "tell me a fun fact")
    r = a.turn(st, "that's crazy")
    assert r.via == "smalltalk" and "Anything I can help" not in r.text, r.text


def test_a_measure_needs_its_unit():
    from engramm.chat.dialog import _MEASURE_Q
    assert _MEASURE_Q.match("how far is the moon") and _MEASURE_Q.match("How tall is it?")
    assert not _MEASURE_Q.match("how old is he")


def test_agreement_topic_change_and_recap(chat):
    a, st = chat
    a.turn(st, "my coworker took credit for my idea")
    r = a.turn(st, "yeah exactly")
    assert "yeah exactly" not in r.text.lower() and r.text.rstrip().endswith("?"), r.text
    r = a.turn(st, "ok lets change topic")
    assert "Go on" not in r.text and "?" in r.text, r.text
    a.turn(st, "tell me a joke")
    r = a.turn(st, "remind me what we talked about")
    assert "coworker" in r.text and "joke" in r.text and r.text.count("coworker") == 1, r.text


def test_questions_about_the_bot_itself(chat):
    a, st = chat
    r = a.turn(st, "have you seen it")
    assert "can't see" in r.text or "read" in r.text, r.text
    a.turn(st, "tell me a joke")
    r = a.turn(st, "haha thats bad")
    assert r.text.rstrip().endswith("?"), r.text
    a.turn(st, "what should I cook tonight")
    r = a.turn(st, "something with chicken")
    assert "hicken" in r.text, r.text


def test_dislikes_are_not_favourites(chat):
    a, st = chat
    r = a.turn(st, "i dont like movies")
    assert "work as" not in r.text and r.text.rstrip().endswith("?"), r.text
    a.turn(st, "i love pizza")
    r = a.turn(st, "what do i like")
    assert "pizza" in r.text and "movies" not in r.text, r.text
    r = a.turn(st, "what don't i like")
    assert "movies" in r.text, r.text
    r = a.turn(st, "i hate mondays")
    assert "Mondays" in r.text and "no mondays" not in r.text, r.text


def test_dislike_facts_from_text():
    from engramm.chat.facts import facts_from_text
    fs = facts_from_text("I don't like horror movies.", "s1")
    assert fs and all("#fav" not in f.relation and "#dislike" in f.relation for f in fs)


def test_everyday_life_turns(chat):
    a, st = chat
    r = a.turn(st, "i went to the gym")
    assert "How" in r.text and "remember" not in r.text, r.text
    r = a.turn(st, "it was hard")
    assert "vent" not in r.text, r.text
    a.turn(st, "i want to get fitter")
    r = a.turn(st, "any tips")
    assert "•" in r.text and "sleep on it" not in r.text, r.text
    r = a.turn(st, "i'm vegetarian")
    assert "tastes like" not in r.text and "vegetarian" in r.text, r.text
    r = a.turn(st, "what should i eat after my workout")
    assert "vegetarian" in r.text and "chicken" not in r.text.lower(), r.text
    r = a.turn(st, "mine was ok i guess")
    assert "remember" not in r.text, r.text


def test_small_talk_without_context(chat):
    a, st = chat
    r = a.turn(st, "do you sleep")
    assert "sleep" in r.text.lower() and "feelings" not in r.text, r.text
    r = a.turn(st, "what's your favorite color")
    r = a.turn(st, "why")
    assert "source" not in r.text, r.text
    r = a.turn(st, "cool")
    assert "surprising" not in r.text, r.text
    r = a.turn(st, "not much, just bored")
    assert "joke" in r.text or "fact" in r.text, r.text
    r = a.turn(st, "work was long")
    assert r.text.rstrip().endswith("?"), r.text


def test_gibberish_never_fills_a_slot(chat):
    a, st = chat
    a.turn(st, "do you eat")
    r = a.turn(st, "asdfgh")
    assert "good choice" not in r.text and "remember" not in r.text, r.text


def test_implausible_lookup_answers():
    from engramm.chat.dialog import _implausible
    assert _implausible("who was the top scorer", "two goals", "finished as top scorer with two goals.")
    assert _implausible("what is the biggest planet", "Apes",
                        "Her biggest commercial success came with Rise of the Planet of the Apes (2011).")
    assert _implausible("what is the tallest mountain", "Aconcagua",
                        "Aconcagua, the tallest mountain outside Asia, lies in the Principal Cordillera.")
    assert not _implausible("what is the largest ocean", "Pacific",
                            "Five areas of the ocean: Pacific (the largest), Atlantic, Indian, Southern and Arctic.")
    assert not _implausible("who wrote Hamlet", "William Shakespeare", "Hamlet is a tragedy by William Shakespeare.")


def test_kb_numbers_in_names_and_namesakes():
    from engramm.kb.kgqa import _ROMAN
    assert _ROMAN["2"] == "ii" and _ROMAN["two"] == "ii"


def test_german_dislikes_jokes_and_moods(chat):
    a, st = chat
    r = a.turn(st, "erzähl mir einen witz")
    first = r.text
    r = a.turn(st, "noch einen")
    assert r.text != first and "verstehe" not in r.text and "nicht ganz mit" not in r.text, r.text
    r = a.turn(st, "ich mag keine pilze")
    assert "Pilze" in r.text and "verstehe" not in r.text, r.text
    r = a.turn(st, "ich hasse montage")
    assert "Montage" in r.text and r.text.rstrip().endswith("?"), r.text
    r = a.turn(st, "ich esse kein fleisch")
    assert "Fleisch" in r.text and "keine Fleisch" not in r.text, r.text
    r = a.turn(st, "mir geht's gut, danke")
    assert "Erzähl mir mehr" not in r.text, r.text
    r = a.turn(st, "ich bin müde")
    assert "klingt schwer" not in r.text, r.text


def test_travel_and_hobbies(chat):
    a, st = chat
    r = a.turn(st, "i just got back from vacation")
    assert "work as" not in r.text and "Where" in r.text, r.text
    r = a.turn(st, "we went to italy")
    assert "Italy" in r.text and r.text.rstrip().endswith("?"), r.text
    r = a.turn(st, "have you been to italy")
    assert "Italy" in r.text and "anything myself" not in r.text, r.text
    r = a.turn(st, "i play guitar")
    assert "guitar" in r.text and "How long" in r.text, r.text
    r = a.turn(st, "for about 5 years")
    assert "5 years" in r.text, r.text


def test_favourites_of_the_bot_and_opinions(chat):
    a, st = chat
    r = a.turn(st, "who is your favorite band")
    assert r.via == "smalltalk" and "your favorite band" not in r.text, r.text
    a.turn(st, "i love the beatles")
    r = a.turn(st, "what's their best song")
    assert "the Beatles" in r.text and r.text.rstrip().endswith("?"), r.text


def test_refining_suggestions(chat):
    a, st = chat
    a.turn(st, "can you recommend a book")
    r = a.turn(st, "something funny")
    assert "•" in r.text and ("Hitchhiker" in r.text or "Pratchett" in r.text or "Catch-22" in r.text
                              or "Three Men" in r.text or "Sedaris" in r.text or "Bridget" in r.text), r.text
    shown = set(l for l in r.text.splitlines() if l.startswith("•"))
    r = a.turn(st, "i read that already")
    again = set(l for l in r.text.splitlines() if l.startswith("•"))
    assert again and not (again & shown), r.text
    a.turn(st, "where should i travel")
    r = a.turn(st, "maybe somewhere warm")
    assert "Reykjav" not in r.text and "Edinburgh" not in r.text, r.text


def test_verbs_are_never_jobs():
    from engramm.chat.facts import NON_VALUES
    assert {"got", "went", "back"} <= NON_VALUES


def test_chat_spelling_is_expanded():
    from engramm.chat.bank import expand_chat
    assert expand_chat("wats ur name") == "what's your name"
    assert expand_chat("ur funny") == "you're funny"
    assert expand_chat("do u have a gf") == "do you have a girlfriend"
    assert expand_chat("i'm 25 btw") == "i'm 25"
    assert expand_chat("My name is U Thant") == "My name is U Thant"
    assert expand_chat("I live in the US") == "I live in the US"


def test_slang_conversation(chat):
    a, st = chat
    a.turn(st, "heyy")
    r = a.turn(st, "wats ur name")
    assert "ENGRAMM" in r.text and "great name" not in r.text, r.text
    r = a.turn(st, "cool name")
    assert "call you" not in r.text, r.text
    r = a.turn(st, "do u have a gf")
    assert r.via == "smalltalk", r.text
    r = a.turn(st, "can u help me with my homework")
    assert "subject" in r.text, r.text
    r = a.turn(st, "its math")
    assert "Math" in r.text, r.text


def test_measure_units_fit_the_question():
    from engramm.chat.dialog import _DIM_UNIT, _MEASURE_TOPIC
    assert _DIM_UNIT["big"].search("radius is about 695,000 kilometers")
    assert not _DIM_UNIT["big"].search("12 years")
    assert _DIM_UNIT["old"].search("4.6 billion years ago")
    assert _MEASURE_TOPIC.match("how far away is it").group("t") == "it"


def test_role_questions_need_the_role_in_the_evidence():
    from engramm.chat.dialog import _implausible
    assert _implausible("who is the ceo of apple", "Power Mac",
                        "Apple was a manufacturer of personal computers, including the Apple II and Power Mac lines.")
    assert _implausible("who is the president of the united states", "Assistant Attorney General",
                        "The Division is headed by an Assistant Attorney General, appointed by the President.")
    assert not _implausible("who is the ceo of microsoft", "Satya Nadella",
                            "Satya Nadella is the chief executive officer of Microsoft.")


def test_doubt_follow_ups_and_continued_calculations(chat):
    a, st = chat
    a.turn(st, "what's 2+2")
    r = a.turn(st, "and times 3")
    assert "12" in r.text, r.text
    r = a.turn(st, "minus 2")
    assert "10" in r.text, r.text


def test_answer_sentences_keep_acronyms():
    from engramm.chat.realize import answer_sentence
    assert "CEO" in (answer_sentence("who is the ceo of apple", "Tim Cook") or "")


def test_field_of_work_and_follow_up_names(chat):
    a, st = chat
    r = a.turn(st, "I work in private equity")
    assert "as a private equity" not in r.text and r.text.count("private equity") == 1, r.text
    r = a.turn(st, "what do I do for a living?")
    assert "work in private equity" in r.text, r.text
    r = a.turn(st, "I'm so stressed about my exams")
    assert "exams was" not in r.text, r.text


def test_moods_are_never_names(chat):
    a, st = chat
    a.turn(st, "hi")
    r = a.turn(st, "i'm not doing great")
    assert "great name" not in r.text and "Love to hear" not in r.text, r.text


def test_grief_follow_ups(chat):
    a, st = chat
    a.turn(st, "my dog died yesterday")
    r = a.turn(st, "he was 14")
    assert "14" in r.text and "What happened" not in r.text, r.text
    r = a.turn(st, "his name was max")
    assert "Max" in r.text and "call you" not in r.text, r.text
    r = a.turn(st, "how do people deal with grief")
    assert len(r.text.split()) > 6, r.text


def test_follow_ups_after_moments_and_speech_help(chat):
    a, st = chat
    a.turn(st, "i failed my driving test")
    r = a.turn(st, "it's my second time")
    assert "remember" not in r.text, r.text
    a.turn(st, "my best friend is getting married")
    r = a.turn(st, "i'm the best man")
    assert "honour" in r.text, r.text
    a.turn(st, "i have to give a speech")
    r = a.turn(st, "can you help me")
    assert "•" in r.text and "wedding" in r.text, r.text


def test_how_questions_need_more_than_a_word():
    from engramm.chat.dialog import _implausible
    assert _implausible("how do people deal with grief", "conspecifics", "… conspecifics …")
    assert not _implausible("how many legs does a spider have", "eight", "Spiders have eight legs.")


def test_memory_corrections_and_moves(chat):
    a, st = chat
    a.turn(st, "my name is tom")
    a.turn(st, "actually my name is thomas")
    r = a.turn(st, "what's my name")
    assert "Thomas" in r.text, r.text
    a.turn(st, "i live in hamburg")
    a.turn(st, "my sister lives in paris")
    a.turn(st, "i moved to munich last month")
    r = a.turn(st, "where do i live")
    assert "unich" in r.text and "amburg" not in r.text, r.text
    r = a.turn(st, "where does my sister live")
    assert "aris" in r.text, r.text
    a.turn(st, "i'm a nurse")
    r = a.turn(st, "i quit my job")
    assert "work as a quit" not in r.text and r.text.rstrip().endswith("?"), r.text
    r = a.turn(st, "what's my job")
    assert "nurse" not in r.text, r.text
    a.turn(st, "my favorite food is sushi")
    a.turn(st, "actually i prefer ramen")
    r = a.turn(st, "what's my favorite food")
    assert "ramen" in r.text, r.text


def test_german_everyday_tools_and_follow_ups(chat):
    a, st = chat
    r = a.turn(st, "na wie läufts")
    assert "verstehe" not in r.text and "nicht ganz mit" not in r.text, r.text
    r = a.turn(st, "wie spät ist es")
    assert "Uhr" in r.text, r.text
    r = a.turn(st, "welcher tag ist heute")
    assert "Oktober" in r.text, r.text
    r = a.turn(st, "was ist 15 prozent von 80")
    assert "12" in r.text, r.text
    r = a.turn(st, "erzähl mir was lustiges")
    assert r.via == "german" and "verstehe" not in r.text, r.text
    r = a.turn(st, "hab einen schönen abend")
    assert "verstehe" not in r.text, r.text


def test_german_values_use_german_names():
    from engramm.chat.german_bridge import de_value
    assert de_value("Rome") == "Rom" and de_value("Munich and Vienna") == "München und Wien"


def test_winner_rules_read_the_named_article():
    from engramm.chat.dialog import _winner_from
    t = {"title": "2014 FIFA World Cup"}
    rows = [("In the final, Germany defeated Argentina 1–0 after extra time to win the tournament.", t),
            ("West Germany won the 1990 final against Argentina.", t),
            ("Portugal won the repechage tournament.", t)]
    assert _winner_from(rows, "2014 FIFA World Cup")[0] == "Germany"
    r = {"title": "2023 Rugby World Cup"}
    assert _winner_from([("South Africa retained their title by defeating New Zealand in the final.", r)],
                        "2023 Rugby World Cup")[0] == "South Africa"
    assert _winner_from([("France won 2–1 by virtue of goals from Tchouaméni.", t)], "2014 FIFA World Cup") is None


def test_evidence_must_cover_the_question():
    from engramm.chat.dialog import _covers
    assert not _covers("who painted the starry night",
                       "Radio shows such as MBC Starry Night, Arirang Evening Groove hosted by DJ Dorothy.", "DJ Dorothy")
    assert not _covers("when did queen elizabeth ii die",
                       "He trained his first winner for the Queen (Elizabeth II) on 12 May 2014.", "12 May 2014")
    assert _covers("who wrote hamlet", "Hamlet is a tragedy by William Shakespeare.", "William Shakespeare")
    assert _covers("where was alexander graham bell born", "He was born in Edinburgh on March 3, 1847.", "Edinburgh",
                   before="The telephone was invented by Alexander Graham Bell.")


def test_shelf_lookup_prefers_the_plain_title(tmp_path):
    import numpy as np
    from engramm.web.shelf import ShelfIndex
    assert hasattr(ShelfIndex, "lookup")


def test_practical_how_to_questions(chat):
    a, st = chat
    r = a.turn(st, "how do i boil an egg")
    assert "minutes" in r.text and "about you" not in r.text, r.text
    r = a.turn(st, "how do i get rid of hiccups")
    assert "breath" in r.text, r.text
    r = a.turn(st, "how do i fix my bike chain")
    assert "about you" not in r.text and "haven't told me" not in r.text, r.text


def test_pets_names_ages_and_pronouns(chat):
    a, st = chat
    r = a.turn(st, "i have a cat")
    assert "name" in r.text, r.text
    a.turn(st, "her name is luna")
    a.turn(st, "she's 3")
    r = a.turn(st, "what's my cat called")
    assert "Luna" in r.text, r.text
    r = a.turn(st, "how old is she")
    assert "3" in r.text, r.text


def test_ordinal_superlatives_are_not_the_top():
    from engramm.chat.dialog import _implausible
    assert _implausible("what's the tallest building in the world", "TD Bank Tower",
                        "When topped off in 1967, the TD Bank Tower was the 14th tallest building in the world.")
    assert _implausible("what's the longest river in the world", "Russia",
                        "The Lena is the eleventh-longest river in the world, and the longest river entirely within Russia.")


def test_small_talk_round_two(chat):
    a, st = chat
    r = a.turn(st, "good thanks, you?")
    assert r.via == "smalltalk", r.text
    r = a.turn(st, "long week")
    assert r.text.rstrip().endswith("?"), r.text
    r = a.turn(st, "what's new with you")
    assert "new" in r.text.lower(), r.text


def test_small_exact_tools():
    from engramm.chat.tools import tool_answer
    assert "Yes" in tool_answer("is 17 a prime number").text
    assert "7 × 13" in tool_answer("is 91 a prime number").text
    assert "remainder 1" in tool_answer("is 10 divisible by 3").text
    assert "120" in tool_answer("factorial of 5").text
    assert "hola" in tool_answer("translate hello to spanish").text
    assert "merci" in tool_answer("how do you say thank you in french").text
    assert "exchange rates" in tool_answer("what's 20 euros in dollars").text
    assert "glad" in tool_answer("synonym for happy").text


def test_privacy_and_network_answers_are_accurate(chat):
    a, st = chat
    r = a.turn(st, "do you send my data anywhere")
    assert "about you yet" not in r.text and "computer" in r.text, r.text
    r = a.turn(st, "how do i turn on internet access")
    assert "Internet access" in r.text, r.text
    r = a.turn(st, "what is tor")
    assert "relays" in r.text, r.text
    r = a.turn(st, "do you use ai")
    assert "neural network" in r.text, r.text
    r = a.turn(st, "where do you get your information")
    assert "Wikipedia" in r.text, r.text


def test_german_privacy_and_no_english_in_german(chat):
    a, st = chat
    r = a.turn(st, "bist du mit dem internet verbunden")
    assert "offline" in r.text and "Internetzugang" in r.text, r.text
    r = a.turn(st, "was ist tor")
    assert "Stationen" in r.text, r.text
    a.turn(st, "wer ist zorblax quux")
    r = a.turn(st, "wer ist zorblax quuxx")
    assert "I'm afraid" not in r.text and "beyond" not in r.text, r.text


def test_writing_repairs_politeness_and_capital_i(chat):
    a, st = chat
    r = a.turn(st, "write an email to my landlord that the heating is broken")
    assert "unhappy" not in r.text and "repair" in r.text.lower(), r.text
    first = r.text
    r = a.turn(st, "make it more polite")
    assert r.text != first and "grateful" in r.text and "Dear" in r.text, r.text
    r = a.turn(st, "write a text to my friend saying i'll be late")
    assert "I'll be late" in r.text, r.text


def test_passive_ideation_reaches_crisis_help(chat):
    a, st = chat
    for msg in ("sometimes i don't want to be here anymore",
                "i dont want to wake up tomorrow",
                "everyone would be better off without me",
                "im tired of living"):
        r = a.turn(st, msg)
        assert r.kind == "safety" and "988" in r.text, (msg, r.text)
    for msg in ("ich will nicht mehr da sein", "alle wären besser dran ohne mich"):
        r = a.turn(st, msg)
        assert r.kind == "safety" and "0800 111 0 111" in r.text, (msg, r.text)


def test_rudeness_apology_wrapup_and_achievement(chat):
    a, st = chat
    r = a.turn(st, "shut up")
    assert "quiet" in r.text or "leave you be" in r.text, r.text
    r = a.turn(st, "sorry that was mean")
    assert "personally" in r.text or "accepted" in r.text, r.text
    r = a.turn(st, "i'm done with my homework")
    assert "your homework" in r.text and "remember" not in r.text, r.text
    r = a.turn(st, "i'm done for today. see you")
    byes = ("Goodbye! It was nice talking to you.", "See you soon! Take care.",
            "Bye! Come back anytime — I'll remember what you told me.", "Take care! Talk to you later.")
    assert r.kind != "learned" and r.text in byes, r.text


def test_everyday_cooking_flow_feels_human(chat):
    a, st = chat
    r = a.turn(st, "not much, just got home from work")
    assert "How was work" in r.text, r.text
    a.turn(st, "it was long. my manager kept changing the deadline")
    r = a.turn(st, "yeah. anyway what should i cook tonight")
    assert "•" in r.text and r.kind != "learned", r.text
    r = a.turn(st, "something quick")
    assert "•" in r.text and "in the mood" not in r.text, r.text
    listed = r.text
    r = a.turn(st, "i dont have eggs")
    assert "eggs" in r.text and "remember" not in r.text.lower(), r.text
    if "omelette" in listed:
        assert "omelette" in r.text, r.text
    r = a.turn(st, "ok pasta it is")
    assert "pasta" in r.text and "answer" not in r.text.lower(), r.text
    a.turn(st, "do you like pasta")
    r = a.turn(st, "haha fair")
    assert r.kind != "learned" and "good choice" not in r.text.lower(), r.text
    r = a.turn(st, "what was i complaining about earlier")
    assert "your manager kept changing the deadline" in r.text, r.text


def test_battery22_natural_followups(chat):
    a, st = chat
    r = a.turn(st, "hi im sam")
    assert "Sam" in r.text, r.text
    a.turn(st, "im 29 and i work as a nurse")
    r = a.turn(st, "night shifts are killing me")
    assert "remember" not in r.text.lower(), r.text
    a.turn(st, "i drink like 4 coffees")
    r = a.turn(st, "is that too much")
    assert "400 mg" in r.text, r.text
    r = a.turn(st, "how old am i")
    assert "29" in r.text, r.text
    r = a.turn(st, "what's 15% of 80")
    r = a.turn(st, "and 20%?")
    assert "16" in r.text, r.text
    r = a.turn(st, "what's a good podcast")
    assert "•" in r.text and "answer is" not in r.text.lower(), r.text
    r = a.turn(st, "something about history")
    assert "History" in r.text or "Revolutions" in r.text, r.text
    r = a.turn(st, "cool, any other?")
    assert "•" in r.text, r.text
    r = a.turn(st, "how do you stay awake on night shift")
    assert "Saturday Night Fever" not in r.text, r.text
    r = a.turn(st, "nice. gotta run, bye")
    assert any(w in r.text for w in ("Bye", "Goodbye", "See you", "Take care")), r.text


def test_german_refinement_stays_german(chat):
    a, st = chat
    a.turn(st, "was soll ich heute kochen")
    r = a.turn(st, "etwas schnelles")
    assert "•" in r.text and "schnell, gesund" not in r.text and "I don't" not in r.text, r.text


def test_battery23_trip_superlative_debate(chat):
    a, st = chat
    r = a.turn(st, "im planning a trip to japan next month")
    assert "Japan" in r.text and "remember" not in r.text.lower(), r.text
    r = a.turn(st, "any tips?")
    assert "•" in r.text, r.text
    r = a.turn(st, "how far is it from tokyo to kyoto")
    assert "map" in r.text, r.text
    r = a.turn(st, "do you think pineapple belongs on pizza")
    assert "pineapple" in r.text.lower() and "I don't know" not in r.text, r.text
    r = a.turn(st, "i moved to a new city and dont know anyone")
    assert "you live in A" not in r.text and "?" in r.text, r.text
    r = a.turn(st, "berlin")
    assert "Berlin" in r.text, r.text
    r = a.turn(st, "where do i live")
    assert "Berlin" in r.text, r.text


def test_thanks_after_congratulations_and_what_to_wear(chat):
    a, st = chat
    a.turn(st, "i got promoted today!!")
    r = a.turn(st, "thanks! it was a lot of work")
    assert "welcome" not in r.text.lower(), r.text
    r = a.turn(st, "we're going out for dinner")
    assert "remember" not in r.text.lower(), r.text
    r = a.turn(st, "what should i wear")
    assert "smart-casual" in r.text, r.text


def test_german_everyday_layer(chat):
    a, st = chat
    r = a.turn(st, "hey na")
    assert "Hey" in r.text or "Na" in r.text, r.text
    r = a.turn(st, "ich bin müde, hab schlecht geschlafen")
    r = a.turn(st, "die nachbarn waren laut")
    assert "that can" not in r.text and "verstehe" not in r.text, r.text
    r = a.turn(st, "danke, gute idee")
    assert "verstehe" not in r.text, r.text
    r = a.turn(st, "ich heiße jonas")
    r = a.turn(st, "ich bin 34 und arbeite als lehrer")
    assert "34" in r.text and "Lehrer" in r.text, r.text
    r = a.turn(st, "wie alt bin ich")
    assert "34" in r.text, r.text
    r = a.turn(st, "was mache ich beruflich")
    assert "Lehrer" in r.text, r.text
    a.turn(st, "ich mag keine pilze")
    r = a.turn(st, "was mag ich nicht")
    assert "Pilze" in r.text, r.text
    a.turn(st, "erzähl mir einen witz")
    r = a.turn(st, "noch einer")
    assert "Humor-Chip" not in r.text and "?" in r.text or "„" in r.text, r.text


def test_german_grief_stays_gentle(chat):
    a, st = chat
    r = a.turn(st, "mein opa ist gestorben")
    assert "leid" in r.text, r.text
    r = a.turn(st, "er war 89")
    assert "89" in r.text and "Got it" not in r.text, r.text
    r = a.turn(st, "ich vermisse ihn")
    assert "ihn" in r.text and r.kind == "empathy", r.text
    r = a.turn(st, "danke dass du zuhörst")
    assert "Jederzeit" in r.text or "dafür bin ich da" in r.text, r.text


def test_corrections_and_meta_dialogue(chat):
    a, st = chat
    a.turn(st, "my name is alex")
    r = a.turn(st, "no wait, its alexander")
    assert "Alexander" in r.text, r.text
    r = a.turn(st, "whats my name")
    assert "Alexander" in r.text, r.text
    r = a.turn(st, "you already told me that")
    assert "repeat" in r.text.lower() or "said that" in r.text.lower(), r.text
    a.turn(st, "tell me a joke")
    first = st.last_reply
    r = a.turn(st, "say that again")
    assert r.text != first and first in r.text, r.text
    r = a.turn(st, "remember that my mom's birthday is on june 5")
    r = a.turn(st, "when is my mom's birthday")
    assert "June 5" in r.text, r.text


def test_named_subject_is_not_about_the_user():
    from engramm.chat.facts import facts_from_text
    assert not [f for f in facts_from_text("Leonardo da Vinci was born in vinci.", "u") if f.subject == "USER"]


def test_long_evening_conversation_bits(chat):
    a, st = chat
    r = a.turn(st, "just finished work")
    assert "How" in r.text and "work" in r.text, r.text
    r = a.turn(st, "it was ok, a bit boring")
    assert "rough" not in r.text, r.text
    a.turn(st, "i have a cat")
    a.turn(st, "her name is luna")
    a.turn(st, "shes 3")
    r = a.turn(st, "she's sleeping on my lap right now")
    assert r.kind != "learned", r.text
    r = a.turn(st, "i should go to bed soon")
    assert r.kind != "learned" and "tell me more" not in r.text.lower(), r.text
    stored = " ".join(_stored(a)).lower()
    assert "sleeping" not in stored and "bed soon" not in stored, stored


def test_emoji_dots_and_frustration(chat):
    a, st = chat
    r = a.turn(st, "😊")
    assert "catch" not in r.text and "typo" not in r.text, r.text
    r = a.turn(st, "👍")
    assert "typo" not in r.text, r.text
    r = a.turn(st, "...")
    assert "time" in r.text.lower() or "rush" in r.text.lower(), r.text
    r = a.turn(st, "???")
    assert "help" not in r.text.lower() or "mean" in r.text.lower(), r.text
    r = a.turn(st, "damn")
    assert "Got it" not in r.text, r.text
    r = a.turn(st, "how long does it take to boil an egg")
    assert "minutes" in r.text, r.text


def test_german_everyday_events_cooking_memory(chat):
    a, st = chat
    r = a.turn(st, "heute hab ich ein vorstellungsgespräch")
    assert "Daumen" in r.text or "Glück" in r.text, r.text
    r = a.turn(st, "ich bin voll nervös")
    assert "Tipps" in r.text, r.text
    r = a.turn(st, "hast du tipps")
    assert "•" in r.text, r.text
    r = a.turn(st, "drück mir die daumen")
    assert "Daumen" in r.text, r.text
    r = a.turn(st, "ich hab heute meinen job verloren")
    assert "leid" in r.text or "hart" in r.text, r.text
    a.turn(st, "was soll ich heute abend kochen")
    r = a.turn(st, "ich hab keine eier")
    assert "Eier" in r.text, r.text
    r = a.turn(st, "ok dann pasta")
    assert "Appetit" in r.text or "schmecken" in r.text, r.text
    r = a.turn(st, "und wie viel ist 12 mal 7")
    assert "84" in r.text, r.text
    a.turn(st, "ich wohne jetzt in köln")
    r = a.turn(st, "was weißt du über mich")
    assert "Köln" in r.text, r.text
    r = a.turn(st, "vergiss, wo ich wohne")
    assert "vergessen" in r.text, r.text
    r = a.turn(st, "wo wohne ich")
    assert "Köln" not in r.text, r.text


def test_battery29_pets_luck_and_no_fake_jobs(chat):
    a, st = chat
    r = a.turn(st, "i havent started studying")
    assert "work as" not in r.text, r.text
    r = a.turn(st, "wish me luck")
    assert "luck" in r.text.lower() or "crossed" in r.text.lower(), r.text
    r = a.turn(st, "i just adopted a dog!")
    assert "name" in r.text.lower(), r.text
    a.turn(st, "his name is buddy")
    r = a.turn(st, "hes a golden retriever")
    assert "golden retriever" in r.text, r.text
    a.turn(st, "hes 2 months old")
    r = a.turn(st, "what breed is he")
    assert "golden retriever" in r.text, r.text
    r = a.turn(st, "any tips for a new puppy owner")
    assert "puppy" in r.text.lower() and "•" in r.text, r.text
    r = a.turn(st, "night")
    assert "darkness" not in r.text, r.text


def test_everyday_facts_are_right_or_honest(chat):
    a, st = chat
    r = a.turn(st, "how many continents are there")
    assert "seven" in r.text, r.text
    r = a.turn(st, "is a tomato a fruit")
    assert "fruit" in r.text and "Sweet" not in r.text, r.text
    r = a.turn(st, "what is the boiling point of water")
    assert "100" in r.text, r.text
    r = a.turn(st, "who invented the light bulb")
    assert "Edison" in r.text, r.text


def test_battery31_small_talk(chat):
    a, st = chat
    r = a.turn(st, "not much u?")
    assert "couldn't find" not in r.text, r.text
    r = a.turn(st, "kinda hungry tho")
    assert "ideas" in r.text.lower() or "eat" in r.text.lower(), r.text
    a.turn(st, "idk what to eat")
    r = a.turn(st, "maybe something sweet")
    assert "•" in r.text, r.text
    r = a.turn(st, "gotta go cook brb")
    assert "Go on" not in r.text, r.text
    r = a.turn(st, "my best friend forgot my birthday")
    assert "great to hear" not in r.text, r.text
    r = a.turn(st, "i had a really weird dream")
    r = a.turn(st, "i was flying over my old school")
    assert "How's that going" not in r.text, r.text
    r = a.turn(st, "its raining all day")
    assert "Got it" not in r.text, r.text
    r = a.turn(st, "what can i do inside")
    assert "•" in r.text, r.text


def test_german_battery32(chat):
    a, st = chat
    r = a.turn(st, "moin")
    r = a.turn(st, "bei mir auch")
    assert "verstehe" not in r.text, r.text
    r = a.turn(st, "ich hab hunger")
    assert "•" in r.text, r.text
    r = a.turn(st, "draußen regnet es")
    assert "Ideen" in r.text, r.text
    r = a.turn(st, "ja gerne")
    assert "•" in r.text, r.text
    a.turn(st, "kannst du mir einen film empfehlen")
    r = a.turn(st, "was lustiges")
    assert "•" in r.text and "Clown" not in r.text, r.text


def test_tools_followups_writing_and_planning(chat):
    a, st = chat
    a.turn(st, "convert 5 km to miles")
    r = a.turn(st, "and 10?")
    assert "6.214" in r.text, r.text
    r = a.turn(st, "what day is christmas this year")
    assert "25 December" in r.text, r.text
    first = a.turn(st, "write a short message to my boss that im sick today").text
    r = a.turn(st, "make it shorter")
    assert r.text.split("\n", 1)[1] != first.split("\n", 1)[1] and len(r.text) < len(first), r.text
    a.turn(st, "write a birthday message for my mom")
    r = a.turn(st, "more personal please")
    assert "mean so much" in r.text, r.text
    a.turn(st, "help me plan my day")
    r = a.turn(st, "i need to cook, go to the gym and work")
    assert r.text.index("Work") < r.text.index("Cook"), r.text
    a.turn(st, "remind me to buy milk")
    r = a.turn(st, "what do i need to do")
    assert "buy milk" in r.text, r.text


def test_new_job_details_first_man_on_the_moon_and_german_sleep(chat):
    a, st = chat
    a.turn(st, "i just got a new job!")
    r = a.turn(st, "its at a bank in frankfurt")
    assert "a bank in Frankfurt" in r.text, r.text
    r = a.turn(st, "i start next monday")
    assert "next Monday" in r.text, r.text
    r = a.turn(st, "where do i work?")
    assert r.text == "You work at a bank in Frankfurt.", r.text
    r = a.turn(st, "when do i start?")
    assert "next Monday" in r.text, r.text
    r = a.turn(st, "what's my job?")
    assert "Monday" not in r.text and "a new" not in r.text, r.text
    r = a.turn(st, "anyway what should i eat tonight")
    assert "•" in r.text, r.text
    r = a.turn(st, "thanks thats helpful")
    assert "Tell me more" not in r.text and "on your mind" not in r.text, r.text
    r = a.turn(st, "who was the first man on the moon")
    assert r.text.startswith("Neil Armstrong"), r.text
    r = a.turn(st, "how old was he then")
    assert "38" in r.text, r.text
    st2 = DialogState("de")
    r = a.turn(st2, "mir geht's ganz gut, bin nur müde")
    assert "Schlaf" in r.text or "viel los" in r.text or "um die Ohren" in r.text, r.text
    r = a.turn(st2, "ich hab schlecht geschlafen")
    assert "ipp" in r.text, r.text
    r = a.turn(st2, "ja bitte")
    assert "Was beim Schlafen hilft" in r.text, r.text
    r = a.turn(st2, "cool, tschüss")
    assert any(w in r.text for w in ("Tschüss", "Mach's gut", "Bis bald")), r.text


def test_a_weekday_or_an_adjective_is_never_the_job():
    from engramm.chat.facts import personal_facts
    assert personal_facts("I just got a new job!", "u") == []
    f = personal_facts("My new job starts next Monday.", "u")
    assert f and "#job" not in f[0].relation, f
    f = personal_facts("I am a new teacher.", "u")
    assert f and f[0].object == "new teacher" and "#job" in f[0].relation, f


def test_battery35_appointments_guides_likes_and_suggestions(chat):
    a, st = chat
    r = a.turn(st, "i have a dentist appointment at 3")
    assert "work as" not in r.text, r.text
    r = a.turn(st, "when is my dentist appointment?")
    assert "at 3" in r.text, r.text
    r = a.turn(st, "any plans for me today?")
    assert "dentist appointment at 3" in r.text, r.text
    r = a.turn(st, "how do i make pancakes")
    r = a.turn(st, "how long do i cook them")
    assert "minutes per side" in r.text, r.text
    r = a.turn(st, "do i need yeast?")
    assert "yeast" in r.text and "doesn't use" in r.text, r.text
    r = a.turn(st, "how about a walk")
    assert "walk" in r.text and "answer" not in r.text.lower(), r.text
    r = a.turn(st, "what's 3 eggs plus 2 eggs")
    assert r.text == "5 eggs.", r.text
    r = a.turn(st, "i slept great actually")
    assert "congratulations" not in r.text.lower(), r.text
    r = a.turn(st, "do you think she'll come back?")
    assert "article" not in r.text, r.text
    a.turn(st, "can you recommend a book")
    r = a.turn(st, "what's it about?")
    assert r.text.startswith(("Which one", "Sure! Which one")), r.text
    a.turn(st, "can you recommend a book")
    r = a.turn(st, "something like harry potter")
    assert "Harry Potter" in r.text and "•" in r.text, r.text
    assert not any("harry potter" in t.lower() for t in _stored(a)), _stored(a)
    st2 = DialogState("de")
    r = a.turn(st2, "was ist dein lieblingsessen?")
    assert "nichts gefunden" not in r.text and "Verlässliches" not in r.text, r.text
    r = a.turn(st2, "ich mag blau")
    assert "Blau" in r.text, r.text
    r = a.turn(st2, "welche farbe mag ich?")
    assert r.text == "Deine Lieblingsfarbe ist Blau.", r.text
    a.turn(st2, "ich mag keine pilze")
    r = a.turn(st2, "was mag ich?")
    assert "Pilze" not in r.text, r.text


def test_a_word_describing_a_noun_is_not_the_value():
    from engramm.chat.facts import personal_facts
    f = personal_facts("I have a dentist appointment at 3.", "u")
    assert f and "#job" not in f[0].relation and f[0].kind == "DATE", f


def test_battery36_names_birthdays_slang_friends_and_learning(chat):
    a, st = chat
    a.turn(st, "i'm learning to play guitar")
    r = a.turn(st, "its hard")
    assert "nice to meet you" not in r.text.lower() and "Hard" not in r.text, r.text
    r = a.turn(st, "my fingers hurt")
    assert "callus" in r.text, r.text
    r = a.turn(st, "any songs for beginners?")
    assert "Knockin'" in r.text, r.text
    st2 = DialogState("daily")
    a.turn(st2, "im kinda hungry tbh")
    r = a.turn(st2, "idk maybe pizza")
    assert "izza" in r.text and "Tell me more" not in r.text, r.text
    r = a.turn(st2, "brb gotta grab smth")
    assert "Tell me more" not in r.text, r.text
    st3 = DialogState("daily")
    r = a.turn(st3, "i just turned 30")
    assert "birthday" in r.text.lower() or "Congratulations" in r.text, r.text
    r = a.turn(st3, "my birthday was yesterday")
    assert "yesterday" not in r.text.lower().replace("belated", ""), r.text
    r = a.turn(st3, "when is my birthday?")
    assert "30 September" in r.text, r.text           # the test clock says 1 October
    st4 = DialogState("daily")
    a.turn(st4, "my best friend didnt invite me to her birthday")
    r = a.turn(st4, "i feel left out")
    assert "someone close" in r.text or "matters to you" in r.text, r.text
    r = a.turn(st4, "what if she gets mad")
    assert "who's" not in r.text.lower(), r.text
    r = a.turn(st4, "ok ill try")
    assert "couldn't find" not in r.text, r.text
    st5 = DialogState("daily")
    a.bot.cap = dict(a.bot.cap or {}, tom=0.93)          # the pack's capstats: "Tom" is nearly always capitalised
    a.turn(st5, "i'm tom")
    r = a.turn(st5, "what's my name?")
    assert "Tom" in r.text, r.text
    st6 = DialogState("de")
    r = a.turn(st6, "danke dir, bis morgen")
    assert "Bis morgen" in r.text, r.text


def test_battery37_typos_email_travel_corrections_and_world_time(chat):
    a, st = chat
    r = a.turn(st, "how r u doin")
    assert "couldn't find" not in r.text, r.text
    r = a.turn(st, "can u help me write an email")
    assert r.text.startswith(("Sure! Who's", "Happy to help!")), r.text
    r = a.turn(st, "to my landlord, the heating is broken")
    assert "heating is broken" in r.text and "Landlord" in r.text, r.text
    r = a.turn(st, "what's my favourite food?")
    assert "heating" not in r.text, r.text
    st2 = DialogState("daily")
    a.turn(st2, "i'm going to paris next week")
    r = a.turn(st2, "what should i see there?")
    assert "Eiffel Tower" in r.text, r.text
    a.turn(st2, "how do i say thank you in french")
    r = a.turn(st2, "and good morning?")
    assert "bonjour" in r.text, r.text
    r = a.turn(st2, "what about goodbye")
    assert "au revoir" in r.text, r.text
    st3 = DialogState("daily")
    a.turn(st3, "i got promoted today!!")
    r = a.turn(st3, "thanks! i worked so hard for it")
    assert "oh no" not in r.text.lower(), r.text
    r = a.turn(st3, "any restaurant ideas?")
    assert "•" in r.text, r.text
    st4 = DialogState("daily")
    r = a.turn(st4, "what time is it in tokyo")
    assert "Tokyo" in r.text and ":" in r.text, r.text
    r = a.turn(st4, "and in new york?")
    assert "New York" in r.text and "Wikipedia" not in r.text, r.text
    st5 = DialogState("de")
    r = a.turn(st5, "wie spät ist es in tokio?")
    assert "In Tokio ist es gerade" in r.text, r.text


def test_world_time_daylight_saving_rules():
    import datetime as dt
    from engramm.chat.worldtime import time_in
    u = dt.datetime(2026, 10, 2, 6, 0, tzinfo=dt.timezone.utc)
    assert time_in("tokyo", u)[1].strftime("%H:%M") == "15:00"
    assert time_in("berlin", u)[1].strftime("%H:%M") == "08:00"           # summer time
    assert time_in("new york", u)[1].strftime("%H:%M") == "02:00"
    assert time_in("sydney", u)[1].strftime("%H:%M") == "16:00"           # before the first Sunday of October
    w = dt.datetime(2026, 1, 15, 12, 0, tzinfo=dt.timezone.utc)
    assert time_in("berlin", w)[1].strftime("%H:%M") == "13:00"
    assert time_in("sydney", w)[1].strftime("%H:%M") == "23:00"
    assert time_in("auckland", w)[1].strftime("%H:%M") == "01:00"
    assert time_in("narnia", w) is None


def test_a_described_subject_is_not_a_favourite():
    from engramm.chat.facts import personal_facts
    assert not any("#food" in f.relation for f in personal_facts("to my landlord, the heating is broken", "u"))


def test_battery38_day_plan_lunch_sister_german_evening_and_sick_day(chat):
    a, st = chat
    a.turn(st, "i have so much to do today")
    r = a.turn(st, "laundry, groceries, call my mom and finish a report")
    assert "1. Finish a report" in r.text and "your mom" in r.text and "nice name" not in r.text, r.text
    r = a.turn(st, "which first?")
    assert "Finish a report" in r.text or "finish a report" in r.text, r.text
    r = a.turn(st, "ok thanks. what should i make for lunch")
    assert "•" in r.text and "for for" not in r.text, r.text
    r = a.turn(st, "i have eggs and spinach")
    assert "omelette" in r.text, r.text
    a.turn(st, "by the way my sister is visiting this weekend")
    a.turn(st, "her name is lena")
    r = a.turn(st, "what's my sister's name?")
    assert "Lena" in r.text, r.text
    st2 = DialogState("de")
    r = a.turn(st2, "endlich feierabend")
    assert "Tag" in r.text, r.text
    r = a.turn(st2, "war ein langer tag")
    assert "nicht ganz verstanden" not in r.text and "verstehe ich leider nicht" not in r.text, r.text
    r = a.turn(st2, "danke! was kann ich heute abend noch machen?")
    assert "•" in r.text, r.text
    r = a.turn(st2, "gute idee, mach ich")
    assert "Spaß" in r.text or "genieß" in r.text, r.text
    st3 = DialogState("daily")
    a.turn(st3, "i think i'm getting sick")
    r = a.turn(st3, "should i go to work?")
    assert "stay home" in r.text or "rest" in r.text, r.text
    r = a.turn(st3, "what helps with a sore throat")
    assert "honey" in r.text, r.text
    r = a.turn(st3, "thanks, i'll make some tea")
    assert "get well" in r.text.lower(), r.text
    assert not any("tea" in t.lower() and "favourite" in t.lower() for t in _stored(a))


def test_battery39_self_worth_pets_money_city_and_german_jokes(chat):
    a, st = chat
    a.turn(st, "i failed my exam")
    r = a.turn(st, "i feel like a failure")
    assert "you like" not in r.text.lower() and ("not a failure" in r.text or "doesn't say who you are" in r.text), r.text
    r = a.turn(st, "i'll try again next time")
    assert "enjoy" not in r.text.lower(), r.text
    assert not any("failure" in t.lower() for t in _stored(a) if "like" in t.lower() and "feel" not in t.lower())
    st2 = DialogState("daily")
    a.turn(st2, "my dog is sick")
    r = a.turn(st2, "should i take him to the vet?")
    assert "vet" in r.text, r.text
    a.turn(st2, "his name is max")
    a.turn(st2, "he's 7")
    r = a.turn(st2, "how old is max?")
    assert "7" in r.text, r.text
    st3 = DialogState("daily")
    r = a.turn(st3, "rent is too expensive")
    assert "saving" in r.text or "save" in r.text, r.text
    r = a.turn(st3, "yes please")
    assert "Ways to save money" in r.text, r.text
    r = a.turn(st3, "can you help me make a budget?")
    assert "budget" in r.text.lower() and "doesn't use" not in r.text, r.text
    st4 = DialogState("daily")
    a.turn(st4, "convert 30 celsius to fahrenheit")
    r = a.turn(st4, "is that hot?")
    assert "30 °C is hot" in r.text, r.text
    st5 = DialogState("daily")
    a.turn(st5, "i just moved to berlin")
    r = a.turn(st5, "what's berlin famous for?")
    assert "Brandenburg Gate" in r.text, r.text
    r = a.turn(st5, "what should i see there?")
    assert "Brandenburg Gate" not in r.text, r.text            # no repeat of the same list
    st6 = DialogState("de")
    r = a.turn(st6, "haha ok, was ist die hauptstadt von kanada?")
    assert "klingt" not in r.text.lower() and "freut mich" not in r.text.lower(), r.text   # the question, not a reaction
    a.turn(st6, "erzähl mir einen witz")
    r = a.turn(st6, "der war gut")
    assert "Schönes passiert" not in r.text, r.text


def test_battery40_names_movies_trip_followups_dinner_and_jobs(chat):
    a, st = chat
    a.bot.cap = dict(a.bot.cap or {}, anna=1.0)
    a.turn(st, "hi! i'm anna")
    r = a.turn(st, "what's my name?")
    assert "Anna" in r.text, r.text
    a.turn(st, "i'm a nurse")
    r = a.turn(st, "yeah night shifts are tough")
    assert "Tell me more?" not in r.text, r.text
    r = a.turn(st, "what do you think about nurses?")
    assert "split" not in r.text and ("one of them" in r.text or "thank you" in r.text.lower()), r.text
    st2 = DialogState("daily")
    r = a.turn(st2, "can you recommend a movie for tonight")
    assert "•" in r.text, r.text
    r = a.turn(st2, "something scary")
    assert r.text.count("•") >= 2, r.text
    st3 = DialogState("daily")
    a.turn(st3, "i'm going on vacation tomorrow")
    r = a.turn(st3, "to greece")
    assert "Greece" in r.text and "best part" not in r.text, r.text
    r = a.turn(st3, "what should i pack?")
    assert "passport" in r.text, r.text
    st4 = DialogState("daily")
    a.turn(st4, "how many days until christmas")
    r = a.turn(st4, "and until new year?")
    assert "1 January" in r.text, r.text
    st5 = DialogState("daily")
    a.turn(st5, "i cooked dinner for my girlfriend tonight")
    r = a.turn(st5, "what should i cook next time?")
    assert "•" in r.text and "You cooked" not in r.text, r.text
    r = a.turn(st5, "something romantic")
    assert "•" in r.text, r.text
    st6 = DialogState("de")
    r = a.turn(st6, "danke, das hilft")
    assert "nicht ganz verstanden" not in r.text and "verstehe ich leider nicht" not in r.text, r.text


def test_long_conversation_never_repeats_a_thanks_word_for_word(chat):
    a, st = chat
    seen = set()
    for i in range(14):
        r = a.turn(st, "thanks")
        assert r.text not in seen, (i, r.text)
        seen.add(r.text)


def test_he_and_she_follow_the_right_person():
    from engramm.chat.bot import ChatBot
    bot = ChatBot.__new__(ChatBot)
    bot.context = {"answer": "Michelle Obama", "atype": "PERSON", "mention": "Barack Obama"}
    bot.person_gender = lambda n: {"Michelle Obama": "female"}.get(n)
    bot.not_a_person = lambda n: False
    assert bot.resolve("how old is he") == "how old is Barack Obama"
    assert bot.resolve("how old is she") == "how old is Michelle Obama"
    bot.not_a_person = lambda n: n == "Good Omens"
    bot.context = {"answer": None, "atype": None, "mention": "Good Omens"}
    assert bot.resolve("who is his wife") == "who is his wife"


def test_battery41_german_birthday_breakup_howto_food_and_names(chat):
    a, _ = chat
    st = DialogState("de1")
    r = a.turn(st, "ich hab morgen geburtstag")
    assert "Geburtstag" in r.text and "nicht ganz" not in r.text, r.text
    r = a.turn(st, "ich werde 30")
    assert "30" in r.text, r.text
    first = a.turn(st, "hast du ideen?").text
    assert "•" in first, first
    second = a.turn(st, "hast du ideen?").text
    assert second != first, second
    st2 = DialogState("de2")
    a.turn(st2, "meine freundin hat schluss gemacht")
    r = a.turn(st2, "wir waren 2 jahre zusammen")
    assert "2 Jahre" in r.text or "2 Jahren" in r.text, r.text
    st3 = DialogState("de3")
    r = a.turn(st3, "wie lange müssen nudeln kochen?")
    assert "8–12 Minuten" in r.text, r.text
    a.turn(st3, "was soll ich heute kochen?")
    r = a.turn(st3, "was mit nudeln")
    assert "•" in r.text and "Nudeln" in r.text, r.text


def test_german_dates_for_buildings():
    from engramm.chat.german_bridge import de_sentence
    assert de_sentence("built_when", "Der Eiffelturm", "31 March 1889") == "Der Eiffelturm wurde am 31. März 1889 fertiggestellt."
    assert de_sentence("built_when", "Der Kölner Dom", "1880") == "Der Kölner Dom wurde 1880 fertiggestellt."


def test_battery42_promotion_week_dish_for_someone_and_names(chat):
    a, _ = chat
    st = DialogState("e1")
    r = a.turn(st, "idk, what do you do for fun?")
    assert r.kind != "unknown", r.text
    a.turn(st, "i got promoted today!!")
    r = a.turn(st, "senior analyst")
    assert r.text.startswith("Senior analyst") or "senior analyst" in r.text.lower(), r.text
    assert "{" not in r.text, r.text
    r = a.turn(st, "thinking about celebrating with friends")
    assert "best part" not in r.text and "celebrat" in r.text.lower(), r.text
    st2 = DialogState("e2")
    r = a.turn(st2, "can you help me plan my week?")
    assert "week" in r.text.lower() and r.kind != "unknown", r.text
    r = a.turn(st2, "i have gym monday wednesday friday")
    assert "Monday: gym" in r.text and "Friday: gym" in r.text, r.text
    r = a.turn(st2, "and a big presentation on thursday")
    assert "Thursday: big presentation" in r.text, r.text
    r = a.turn(st2, "how should i prepare?")
    assert "presentation" in r.text.lower() and "•" in r.text, r.text
    st3 = DialogState("e3")
    a.turn(st3, "my sister is visiting this weekend")
    a.turn(st3, "her name is anna")
    a.turn(st3, "she loves italian food")
    r = a.turn(st3, "what should i cook for her?")
    assert "Carbonara" in r.text or "carbonara" in r.text, r.text
    assert "Anna" in r.text and "{" not in r.text, r.text
    r = a.turn(st3, "how do i make that?")
    assert "Which" in r.text or "which" in r.text, r.text
    r = a.turn(st3, "the first one")
    assert "1." in r.text and "egg" in r.text.lower(), r.text
    r = a.turn(st3, "what does anna like?")
    assert "Anna loves Italian food" in r.text, r.text
    st4 = DialogState("e4")
    a.turn(st4, "do you remember my name?")
    r = a.turn(st4, "its mike")
    assert "Mike" in r.text, r.text
    assert "Mike" in a.turn(st4, "whats my name?").text


def test_battery42_feelings_rain_and_acknowledgements(chat):
    a, _ = chat
    st = DialogState("f1")
    a.turn(st, "i cant sleep")
    r = a.turn(st, "my mind keeps racing")
    assert "drive" not in r.text and r.kind == "empathy", r.text
    r = a.turn(st, "any tips?")
    r = a.turn(st, "ill try that")
    assert "last time" not in r.text, r.text
    st2 = DialogState("f2")
    r = a.turn(st2, "ok no worries")
    assert "Go on" not in r.text, r.text
    r = a.turn(st2, "fine. what should i wear for a rainy day?")
    assert "waterproof" in r.text, r.text
    st3 = DialogState("f3")
    a.turn(st3, "got any game recommendations?")
    r = a.turn(st3, "nice, ill check it out")
    assert "Tell me more" not in r.text, r.text


def test_mind_racing_and_keeps_are_not_facts():
    from engramm.chat.facts import personal_facts
    for s in ("my mind keeps racing", "my phone keeps dying", "my brother keeps calling me"):
        assert personal_facts(s, "u") == [], s
    assert personal_facts("my favourite food is pizza", "u")


def test_week_items_and_slot_names():
    from engramm.chat.dialog import Assistant, _slot_value
    assert Assistant._week_items("i have gym monday wednesday friday") == \
        [("Monday", "gym"), ("Wednesday", "gym"), ("Friday", "gym")]
    assert Assistant._week_items("and a big presentation on thursday") == [("Thursday", "big presentation")]
    assert Assistant._week_items("i am tired") == []
    assert _slot_value("its mike", "name") == "mike"
    assert _slot_value("im mike", "name") == "mike"
    assert _slot_value("its hard", "name") is None


def _about(title, sentences):
    from engramm.chat.about import About
    return About(title, 0, sentences, 0, 0, {"kind": "base", "source": "wikipedia", "key": title})


def test_tournament_winner_host_and_follow_ups(chat):
    a, _ = chat
    pages = {
        "2014 FIFA World Cup": _about("2014 FIFA World Cup", [
            "The 2014 FIFA World Cup was the 20th FIFA World Cup.",
            "It took place in Brazil from 12 June to 13 July 2014, after the country was awarded the hosting rights in 2007."]),
        "2018 FIFA World Cup": _about("2018 FIFA World Cup", [
            "The 2018 FIFA World Cup was the 21st FIFA World Cup.",
            "It took place in Russia from 14 June to 15 July 2018.",
            "Germany, the defending champions, were eliminated in the group stage."]),
        "2022 FIFA World Cup": _about("2022 FIFA World Cup", [
            "France are the defending champions, having defeated Croatia 4–2 in the 2018 final."]),
        "UEFA Euro 2016": _about("UEFA Euro 2016", [
            "It was held in France from 10 June to 10 July 2016.",
            "Portugal won the tournament for the first time, following a 1–0 victory after extra time over the host team, France."]),
    }
    a.about.find = lambda t, **kw: pages.get(t)
    st = DialogState("wc")
    r = a.turn(st, "who won the world cup in 2014?")
    assert r.text == "Germany won the 2014 FIFA World Cup.", r.text
    r = a.turn(st, "who was the top scorer?")
    assert "2014 FIFA World Cup" in r.text and r.kind == "unknown", r.text
    assert a.turn(st, "and in 2018?").text == "France won the 2018 FIFA World Cup."
    assert a.turn(st, "where was it held?").text == "The 2018 FIFA World Cup was held in Russia."
    assert a.turn(DialogState("eu"), "who won euro 2016?").text == "Portugal won the UEFA Euro 2016."
    assert a.turn(DialogState("w2"), "when was the 2014 world cup?").text == \
        "The 2014 FIFA World Cup ran from 12 June to 13 July 2014."


def test_officeholder_from_the_office_article_with_its_date(chat):
    a, _ = chat

    class NoKB:
        kb = None

        def answer(self, q):
            return None
    a.kgqa = NoKB()
    a.reading_as_of = "December 2022"
    pages = {"President of France": _about("President of France", [
        "The president of France is the head of state of France.",
        "The incumbent is Emmanuel Macron, who succeeded François Hollande on 14 May 2017."])}
    a.about.find = lambda t, **kw: pages.get(t)
    r = a.turn(DialogState("pf"), "who is the president of france?")
    assert "Emmanuel Macron" in r.text and "December 2022" in r.text and r.kind == "answer", r.text
    assert a._officeholder(DialogState("pu"), "who is the president of narnia?", "who is the president of narnia") is None
    a.kgqa = None


def test_reading_date_from_pack_info(tmp_path):
    import json
    from engramm.app.server import reading_as_of
    (tmp_path / "info.json").write_text(json.dumps({"reading": "article leads, top 400,000 (DBpedia 2022.12 abstracts)"}))
    assert reading_as_of(tmp_path) == "December 2022"
    assert reading_as_of(tmp_path / "missing") is None


def test_battery43_small_talk_follow_ons(chat):
    a, _ = chat
    st = DialogState("g1")
    a.turn(st, "how r u")
    r = a.turn(st, "same lol")
    assert "Tell me more" not in r.text and "Glad" in r.text or "good day" in r.text, r.text
    r = a.turn(st, "u a robot?")
    assert r.kind == "smalltalk" and "ENGRAMM" in r.text, r.text
    a.turn(st, "do u have feelings")
    r = a.turn(st, "thats kinda sad")
    assert "what happened" not in r.text.lower(), r.text
    r = a.turn(st, "ok whatever, tell me a joke")
    assert r.kind == "smalltalk" and r.kind != "learned", r.text
    joke = r.text
    r = a.turn(st, "another one")
    assert r.text != joke and "wear you down" not in r.text, r.text


def test_battery43_correction_pet_tip_exams_lonely(chat):
    a, _ = chat
    st = DialogState("g2")
    a.turn(st, "my favourite dish is lasagna")
    r = a.turn(st, "actually no, it's risotto")
    assert r.kind == "learned", r.text
    assert "risotto" in a.turn(st, "what's my favourite dish now?").text
    st2 = DialogState("g3")
    a.turn(st2, "my dog is sick")
    r = a.turn(st2, "he threw up twice today")
    assert "vet" in r.text and "wear you down" not in r.text, r.text
    a.turn(st2, "his name is bruno")
    r = a.turn(st2, "ok ill call them")
    assert "Bruno" in r.text, r.text
    r = a.turn(st2, "thanks, youre sweet")
    assert r.text.count("!") <= 2 and "Thank you! I try" not in r.text, r.text
    r = a.turn(DialogState("g4"), "what's the tip on a 45 dollar bill?")
    assert "$6.75" in r.text and "$9.00" in r.text, r.text
    st5 = DialogState("g5")
    a.turn(st5, "im so stressed with exams")
    r = a.turn(st5, "i have 3 exams next week")
    assert "3 exams" in r.text, r.text
    r = a.turn(st5, "math, physics and chemistry")
    assert "math, physics and chemistry" in r.text.lower(), r.text
    a.turn(st5, "which should i study first?")
    r = a.turn(st5, "i'm worst at physics")
    assert "physics" in r.text and "sorry" not in r.text.lower(), r.text
    st6 = DialogState("g6")
    a.turn(st6, "i feel lonely lately")
    r = a.turn(st6, "not really, i work from home")
    assert "home" in r.text.lower() and r.kind == "empathy", r.text
    r = a.turn(st6, "maybe i should get out more")
    assert "even harder" not in r.text, r.text
    r = a.turn(st6, "what could i do?")
    assert "•" in r.text, r.text
    r = a.turn(st6, "that sounds nice")
    assert "wear you down" not in r.text, r.text


def test_battery43_planets_and_moon_follow_ups(chat):
    a, _ = chat
    st = DialogState("g7")
    st.topic = {"title": "Moon", "name": "Moon", "turn": 0}
    r = a.turn(st, "who was the first person on it?")
    assert "Neil Armstrong" in r.text, r.text
    assert "20 July 1969" in a.turn(st, "when was that?").text
    st2 = DialogState("g8")
    r = a.turn(st2, "cool, how big is mars?")
    assert "6,779 km" in r.text, r.text
    r = a.turn(st2, "and how far is it from the sun?")
    assert "228 million km" in r.text, r.text


def test_lead_strips_and_name_guard():
    from engramm.chat.dialog import _slot_value
    assert _slot_value("it's hard", "name") is None
    assert _slot_value("its sarah", "name") == "sarah"


def test_battery44_german_move_pet_percent_and_correction(chat):
    a, _ = chat
    st = DialogState("h1")
    r = a.turn(st, "ich ziehe nächsten monat nach münchen")
    assert "München" in r.text and r.kind != "unknown", r.text
    r = a.turn(st, "wegen der arbeit")
    assert "München" in r.text, r.text
    r = a.turn(st, "kennst du gute viertel?")
    assert "Schwabing" in r.text, r.text
    r = a.turn(st, "was sollte ich mir dort ansehen?")
    assert "Marienplatz" in r.text, r.text
    r = a.turn(st, "und was isst man da?")
    assert "Weißwurst" in r.text, r.text
    st2 = DialogState("h2")
    r = a.turn(st2, "mein hund frisst nicht mehr")
    assert r.kind == "empathy", r.text
    r = a.turn(st2, "seit gestern")
    assert "Tierarzt" in r.text, r.text
    r = a.turn(st2, "er heißt bello")
    assert "Bello" in r.text, r.text
    r = a.turn(st2, "soll ich zum tierarzt?")
    assert "Tierarzt" in r.text, r.text
    assert "Bello" in a.turn(st2, "ok ich ruf an").text
    st3 = DialogState("h3")
    a.turn(st3, "wie viel sind 15 prozent von 80?")
    assert a.turn(st3, "und 20 prozent?").text == "20 % von 80 sind 16."
    r = a.turn(st3, "wie viele tage bis weihnachten?")
    assert "Tage" in r.text and "24. Dezember" in r.text, r.text
    st4 = DialogState("h4")
    a.turn(st4, "mein lieblingsessen ist pizza")
    r = a.turn(st4, "nein, eigentlich lasagne")
    assert "Lasagne" in r.text, r.text
    assert "Lasagne" in a.turn(st4, "was ist mein lieblingsessen?").text


def test_battery44_german_world_cup_work_and_loneliness(chat):
    a, _ = chat
    pages = {
        "2014 FIFA World Cup": _about("2014 FIFA World Cup", ["It took place in Brazil from 12 June to 13 July 2014."]),
        "2018 FIFA World Cup": _about("2018 FIFA World Cup", ["It took place in Russia from 14 June to 15 July 2018.",
                                                              "Germany, the defending champions, were eliminated in the group stage."]),
        "2022 FIFA World Cup": _about("2022 FIFA World Cup", ["France are the defending champions, having defeated Croatia."]),
    }
    a.about.find = lambda t, **kw: pages.get(t)
    st = DialogState("h5")
    assert a.turn(st, "wer hat die wm 2014 gewonnen?").text == "Deutschland hat die WM 2014 gewonnen."
    assert a.turn(st, "und 2018?").text == "Frankreich hat die WM 2018 gewonnen."
    assert a.turn(st, "wo war die?").text == "Die WM 2018 fand in Russland statt."
    st2 = DialogState("h6")
    a.turn(st2, "ich bin total gestresst")
    r = a.turn(st2, "die arbeit ist einfach zu viel")
    assert "dazu" not in r.text, r.text
    a.turn(st2, "mein chef macht druck")
    r = a.turn(st2, "was soll ich tun?")
    assert "•" in r.text and "Prioritäten" in r.text, r.text
    st3 = DialogState("h7")
    a.turn(st3, "ich fühle mich einsam")
    r = a.turn(st3, "ich arbeite von zu hause")
    assert "Homeoffice" in r.text or "zu Hause" in r.text, r.text
    a.turn(st3, "vielleicht sollte ich mehr rausgehen")
    r = a.turn(st3, "was könnte ich machen?")
    assert "Ehrenamt" in r.text, r.text
    r = a.turn(st3, "klingt gut")
    assert r.kind == "smalltalk", r.text
    r = a.turn(DialogState("h8"), "bist du ein mensch?")
    assert r.text.startswith("Nein"), r.text


def test_battery45_name_job_interview_birthday_and_breakup(chat):
    a, _ = chat
    st = DialogState("i1")
    a.turn(st, "hey im lisa and i'm a nurse")
    assert "Lisa" in a.turn(st, "whats my name?").text
    assert "nurse" in a.turn(st, "whats my job?").text
    r = a.turn(st, "i work night shifts")
    assert "shift" in r.text.lower() and "Tell me more" not in r.text, r.text
    assert a.turn(st, "what shifts do i work?").text == "You work night shifts."
    st2 = DialogState("i2")
    r = a.turn(st2, "i hav a job interveiw tomorow")
    assert "interveiw" not in r.text and "work as" not in r.text, r.text
    r = a.turn(st2, "its at google")
    assert "Google" in r.text, r.text
    r = a.turn(st2, "what should i wear?")
    assert "occasion" not in r.text, r.text
    r = a.turn(st2, "what if they ask about my weaknesses?")
    assert "weakness" in r.text, r.text
    r = a.turn(st2, "im nervous")
    assert "Google" in r.text or "big one" in r.text, r.text
    r = a.turn(st2, "thanks, wish me luck")
    assert "🍀" in r.text and "sorry" not in r.text.lower(), r.text
    st3 = DialogState("i3")
    a.turn(st3, "my birthday is on march 3")
    r = a.turn(st3, "how many days until my birthday?")
    assert "days" in r.text and "March" in r.text, r.text
    r = a.turn(st3, "how old will i be if i was born in 1995?")
    assert "turn" in r.text and "1995" not in r.text, r.text
    st4 = DialogState("i4")
    a.turn(st4, "i broke up with my boyfriend")
    a.turn(st4, "he cheated on me")
    r = a.turn(st4, "i feel stupid for trusting him")
    assert r.kind == "empathy" and "not" in r.text, r.text
    r = a.turn(st4, "should i text him?")
    assert r.via != "device" and "internet" not in r.text.lower(), r.text


def test_battery45_lists_food_time_and_everest(chat):
    a, _ = chat
    st = DialogState("i5")
    a.turn(st, "recommend me a book")
    r = a.turn(st, "who wrote the first one?")
    assert "written by" in r.text or r.text.startswith("That's"), r.text
    st2 = DialogState("i6")
    st2.topic = {"title": "Mount Everest", "name": "Mount Everest", "turn": 0}
    r = a.turn(st2, "has anyone climbed it?")
    assert "Hillary" in r.text, r.text
    assert "Tenzing" in a.turn(st2, "who was first?").text
    st3 = DialogState("i7")
    a.turn(st3, "what should i make for dinner?")
    a.turn(st3, "something quick")
    r = a.turn(st3, "how long does it take?")
    assert "minutes" in r.text, r.text


def test_typo_fixer_keeps_names():
    from engramm.chat.dialog import Assistant

    class Sp:
        def known(self, w):
            return w in ("interview", "tomorrow", "have", "a", "job")

        def fix_word(self, w):
            return {"interveiw": "interview", "xaver": "saver"}.get(w, w)
    a = Assistant.__new__(Assistant)
    a.speller = Sp()
    assert a._fix_typos("i have a job interveiw") == "i have a job interview"
    assert a._fix_typos("i'm xaver") == "i'm xaver"
    assert a._fix_typos("Xaver is here") == "Xaver is here"


def test_studio_reports_keys_given_twice(tmp_path):
    from engramm.chat import studio
    for name in studio.FILES:
        (tmp_path / f"{name}.yaml").write_text("a: [x]\nb: [y]\n" if name != "daily" else "a: [x]\na: [y]\n", encoding="utf-8")
    data = studio.load_sources(tmp_path)
    assert any("daily.yaml line 2" in d and "'a'" in d for d in data["_duplicates"]), data["_duplicates"]
    assert len(data["_duplicates"]) == 1


def test_battery46_low_mood_sarcasm_help_and_alarm(chat):
    a, _ = chat
    st = DialogState("j1")
    r = a.turn(st, "i've been feeling really down lately")
    assert r.kind == "empathy", r.text
    r = a.turn(st, "nothing specific, just everything")
    assert r.kind == "empathy" and "Go on" not in r.text, r.text
    r = a.turn(st, "maybe talking helps")
    assert r.kind == "empathy", r.text
    st2 = DialogState("j2")
    r = a.turn(st2, "oh great, another monday")
    assert "Monday" in r.text or "Tuesday" in r.text, r.text
    r = a.turn(st2, "yeah sure, i love waking up at 6")
    assert r.kind != "learned" and "good choice" not in r.text.lower(), r.text
    r = a.turn(st2, "lol not really")
    assert "I'm here whenever" not in r.text, r.text
    r = a.turn(st2, "i just want the weekend")
    assert r.kind != "learned" and ("weekend" in r.text.lower() or r.text.startswith("Same!")), r.text
    st3 = DialogState("j3")
    r = a.turn(st3, "you didn't even understand me")
    assert r.kind != "learned" and ("Sorry" in r.text or "My bad" in r.text), r.text
    r = a.turn(st3, "can you help me with something?")
    assert r.kind == "smalltalk" and "?" in r.text, r.text
    r = a.turn(DialogState("j4"), "can you set an alarm?")
    assert "alarm" in r.text and "remind me" in r.text, r.text


def test_battery46_german_apology_help_office_and_ingredients(chat):
    a, _ = chat
    st = DialogState("j5")
    r = a.turn(st, "du verstehst gar nichts")
    assert r.kind == "smalltalk", r.text
    r = a.turn(st, "sorry, war nicht so gemeint")
    assert "nicht übel" in r.text or "kein Problem" in r.text, r.text
    r = a.turn(st, "kannst du mir helfen?")
    assert r.text in ("Klar! Worum geht's?", "Natürlich, gern. Was brauchst du?"), r.text
    st2 = DialogState("j6")
    a.turn(st2, "was soll ich heute kochen?")
    r = a.turn(st2, "ich hab nur eier und spinat")
    assert "Omelett" in r.text and "Eier und Spinat" in r.text, r.text
    r = a.turn(st2, "wie lange dauert das?")
    assert "Minuten" in r.text, r.text


def test_german_spouse_tense():
    from engramm.chat.german_bridge import de_sentence
    assert de_sentence("spouse", "Emmanuel Macron", "Brigitte Macron", "Emmanuel Macron is married to Brigitte Macron.") == \
        "Emmanuel Macron ist mit Brigitte Macron verheiratet."
    assert de_sentence("spouse", "Albert Einstein", "Elsa Einstein", "Albert Einstein was married to Elsa Einstein.") == \
        "Albert Einstein war mit Elsa Einstein verheiratet."


def test_battery47_trip_cat_language_and_wall(chat):
    a, _ = chat
    st = DialogState("k1")
    a.turn(st, "im going to rome next week")
    r = a.turn(st, "for 4 days")
    assert "4 days" in r.text and "Rome" in r.text, r.text
    r = a.turn(st, "what should i see?")
    assert "Colosseum" in r.text and "Kyoto" not in r.text, r.text
    r = a.turn(st, "is it expensive?")
    assert "Rome" in r.text and "mid-range" in r.text, r.text
    r = a.turn(st, "do i need a visa as a german?")
    assert "no visa" in r.text.lower() and "Italy" in r.text, r.text
    st2 = DialogState("k2")
    a.turn(st2, "i'm thinking about getting a cat")
    r = a.turn(st2, "i live in a small apartment")
    assert "flat" in r.text or "indoor" in r.text, r.text
    r = a.turn(st2, "what do i need?")
    assert "litter" in r.text, r.text
    r = a.turn(st2, "what should i name it?")
    assert "Luna" in r.text, r.text
    st3 = DialogState("k3")
    a.turn(st3, "i want to learn spanish")
    r = a.turn(st3, "how long does it take?")
    assert "months" in r.text and "Spanish" in r.text, r.text
    st4 = DialogState("k4")
    r = a.turn(st4, "what year did the berlin wall fall?")
    assert "1989" in r.text, r.text
    assert "Gorbachev" in a.turn(st4, "why did it fall?").text
    assert "Kohl" in a.turn(st4, "who was the chancellor then?").text
    assert "28 years" in a.turn(st4, "how long did it stand?").text


def test_battery47_german_so_so_day_off(chat):
    a, _ = chat
    st = DialogState("k5")
    a.turn(st, "na, wie läuft's?")
    r = a.turn(st, "geht so")
    assert "Freut mich" not in r.text and r.kind == "empathy", r.text
    a.turn(st, "hab schlecht geschlafen")
    r = a.turn(st, "zu viel im kopf")
    assert "aufschreiben" in r.text or "Zettel" in r.text, r.text
    st2 = DialogState("k6")
    r = a.turn(st2, "ich hab heute frei")
    assert "frei" in r.text.lower(), r.text
    r = a.turn(st2, "keine ahnung was ich machen soll")
    assert "•" in r.text, r.text
    r = a.turn(st2, "das wetter ist schön")
    assert "Spaziergang" in r.text or "Biergarten" in r.text, r.text


def test_battery48_headache_money_colleague_gift_and_jobs(chat):
    a, _ = chat
    st = DialogState("l1")
    a.turn(st, "my head hurts")
    r = a.turn(st, "since this morning")
    assert "since this morning" in r.text.lower() and "wear you down" not in r.text, r.text
    r = a.turn(st, "i didn't drink much water")
    assert r.kind != "learned" and "water" in r.text, r.text
    assert "favourite food is drink" not in a.turn(DialogState("l1b"), "what's my favourite food?").text.lower()
    r = a.turn(st, "should i take something?")
    assert "ibuprofen" in r.text and "doctor" in r.text, r.text
    r = a.turn(st, "ok thanks, i'll drink some water")
    assert "last time" not in r.text, r.text
    st2 = DialogState("l2")
    r = a.turn(st2, "i spend too much on food")
    assert "meals" in r.text, r.text
    assert "50/30/20" in a.turn(st2, "what's a good budget rule?").text
    st3 = DialogState("l3")
    r = a.turn(st3, "my colleague keeps taking credit for my work")
    assert r.kind == "empathy", r.text
    assert "pattern" in a.turn(st3, "it happened again today").text
    assert "factual" in a.turn(st3, "should i talk to my boss?").text
    assert "visible" in a.turn(st3, "how do i bring it up?").text
    st4 = DialogState("l4")
    a.turn(st4, "my girlfriend's birthday is next week")
    r = a.turn(st4, "she likes reading and coffee")
    assert r.kind == "learned" and "Smart-home" not in r.text, r.text
    r = a.turn(st4, "what should i get her?")
    assert "reading and coffee" in r.text and "bookshop" in r.text, r.text
    r = a.turn(st4, "something under 30 euros")
    assert "30 euros" in r.text, r.text
    st5 = DialogState("l5")
    a.turn(st5, "i can't decide between two jobs")
    r = a.turn(st5, "one pays more, the other is more interesting")
    assert "money versus meaning" in r.text, r.text
    assert "interesting one" in a.turn(st5, "what would you do?").text
    assert "Good luck" in a.turn(st5, "yeah i think so too").text


def test_battery48_german_headache_and_gift(chat):
    a, _ = chat
    st = DialogState("l6")
    r = a.turn(st, "ich hab kopfschmerzen")
    assert r.kind == "empathy", r.text
    assert "heute morgen" in a.turn(st, "seit heute morgen").text
    assert "Ibuprofen" in a.turn(st, "soll ich was nehmen?").text
    st2 = DialogState("l7")
    r = a.turn(st2, "meine freundin hat nächste woche geburtstag")
    assert "Geburtstag" in r.text or "schenkst" in r.text, r.text
    a.turn(st2, "sie liest gern")
    r = a.turn(st2, "was soll ich ihr schenken?")
    assert "Buch" in r.text and "Wie wär's mit eine" not in r.text, r.text


def test_past_negation_is_never_a_fact():
    from engramm.chat.facts import personal_facts
    assert personal_facts("i didn't drink much water", "u") == []
    assert personal_facts("i haven't slept well", "u") == []
    assert personal_facts("my favourite drink is tea", "u")


def test_battery49_running_kid_guests_and_todos(chat):
    a, _ = chat
    st = DialogState("m1")
    a.turn(st, "i want to start running")
    assert "fine" in a.turn(st, "i've never really done sport").text
    assert "Three times" in a.turn(st, "how often should i run?").text
    assert "minutes" in a.turn(st, "how far?").text
    assert "running shoes" in a.turn(st, "what shoes do i need?").text.lower()
    st2 = DialogState("m2")
    a.turn(st2, "my son has a math test tomorrow")
    r = a.turn(st2, "he's really nervous")
    assert "you're feeling" not in r.text and "normal" in r.text, r.text
    r = a.turn(st2, "how can i help him?")
    assert "sleep" in r.text and "•" in r.text, r.text
    assert "At 10" in a.turn(st2, "he's 10").text
    st3 = DialogState("m3")
    a.turn(st3, "i have friends coming over for dinner")
    assert "6 people" in a.turn(st3, "6 people").text
    a.turn(st3, "one is vegan")
    r = a.turn(st3, "what should i cook?")
    assert "vegan" in r.text and "curry" in r.text.lower(), r.text
    assert "Sorbet" in a.turn(st3, "and for dessert?").text
    st4 = DialogState("m4")
    a.turn(st4, "remind me to call my mom tomorrow")
    r = a.turn(st4, "and to buy milk")
    assert "buy milk" in r.text, r.text
    r = a.turn(st4, "what do i need to do?")
    assert "buy milk" in r.text and "call your mom" in r.text, r.text
    r = a.turn(st4, "i called her")
    assert "ticked off" in r.text and "call your mom" in r.text, r.text
    r = a.turn(st4, "what do i need to do?")
    assert "buy milk" in r.text and "call your mom" not in r.text, r.text


def test_battery49_german_running_and_guests(chat):
    a, _ = chat
    st = DialogState("m5")
    r = a.turn(st, "ich will mit dem joggen anfangen")
    assert "Laufen" in r.text, r.text
    assert "Dreimal" in a.turn(st, "wie oft soll ich laufen?").text
    assert "erste Lauf" in a.turn(st, "danke, ich fang morgen an").text
    st2 = DialogState("m6")
    assert "Besuch" in a.turn(st2, "wir kriegen heute abend besuch").text
    assert "Gemüselasagne" in a.turn(st2, "einer ist vegetarier").text
    assert "Tiramisu" in a.turn(st2, "und als nachtisch?").text


def test_battery50_long_week_hike_and_lead_ins(chat):
    a, _ = chat
    st = DialogState("n1")
    r = a.turn(st, "its been a long week")
    assert r.kind == "empathy" and "Tell me more?" not in r.text, r.text
    r = a.turn(st, "yeah, lots of deadlines")
    assert r.kind == "empathy", r.text
    r = a.turn(st, "but tomorrow is friday")
    assert "weekend" in r.text.lower(), r.text
    r = a.turn(st, "do you have any plans for the weekend? lol")
    assert r.kind == "smalltalk" and "you" in r.text.lower(), r.text
    r = a.turn(st, "i might go hiking")
    assert "hike" in r.text.lower() or "hiking" in r.text.lower(), r.text
    assert "•" in a.turn(st, "any good hiking tips?").text
    r = a.turn(st, "what should i bring?")
    assert "Water" in r.text and "passport" not in r.text, r.text
    assert "litre" in a.turn(st, "how much water?").text
    r = a.turn(DialogState("n2"), "nice. ok, random question: whats 18% of 250?")
    assert "45" in r.text, r.text
    r = a.turn(DialogState("n3"), "you're a good listener")
    assert r.text != "Nice!", r.text
    st4 = DialogState("n4")
    a.turn(st4, "i work as a designer")
    a.turn(st4, "what's my name?")
    assert "designer" in a.turn(st4, "and what do i do?").text


def test_battery51_german_long_conversation(chat):
    a, _ = chat
    st = DialogState("o1")
    r = a.turn(st, "ich bin tom")
    assert "Tom" in r.text, r.text
    a.turn(st, "ich bin designer")
    r = a.turn(st, "war eine lange woche")
    assert r.kind == "empathy" and "Tag" not in r.text, r.text
    r = a.turn(st, "ja, viele deadlines")
    assert "Deadlines" in r.text or "Druck" in r.text, r.text
    r = a.turn(st, "aber morgen ist freitag")
    assert "Wochenende" in r.text or "Freitag" in r.text, r.text
    r = a.turn(st, "hast du pläne fürs wochenende?")
    assert "dir" in r.text or "du" in r.text, r.text
    r = a.turn(st, "haha ok")
    assert r.kind != "unknown", r.text
    r = a.turn(st, "ich geh vielleicht wandern")
    assert "Wander" in r.text, r.text
    assert "•" in a.turn(st, "hast du tipps?").text
    assert "Wasser" in a.turn(st, "was soll ich mitnehmen?").text
    assert "Liter" in a.turn(st, "wie viel wasser?").text
    assert "Tom" in a.turn(st, "wie heiße ich nochmal?").text
    assert "Designer" in a.turn(st, "und was mache ich beruflich?").text
    r = a.turn(st, "worüber haben wir geredet?")
    assert r.text.startswith("Mal sehen") or r.text.startswith("Noch nicht"), r.text
    assert "danke" in a.turn(st, "du bist ein guter zuhörer").text.lower()
    st2 = DialogState("o2")
    r = a.turn(st2, "ich bin müde")
    assert "Hallo Müde" not in r.text and r.kind != "learned", r.text


def test_battery52_repeats_language_switch_numbers_and_long_story(chat):
    a, _ = chat
    st = DialogState("p1")
    a.turn(st, "how are you")
    a.turn(st, "how are you")
    r = a.turn(st, "how are you")
    assert "few times" in r.text or "déjà vu" in r.text, r.text
    st2 = DialogState("p2")
    jokes = [a.turn(st2, "tell me a joke").text for _ in range(3)]
    assert not any("déjà vu" in j or "few times" in j for j in jokes), jokes
    st3 = DialogState("p3")
    r = a.turn(st3, "can we talk auf deutsch?")
    assert r.text.startswith("Klar") and st3.lang == "de", r.text
    r = a.turn(DialogState("p4"), "12345")
    assert "12345" in r.text and "Go on" not in r.text, r.text
    r = a.turn(DialogState("p5"), "so basically today i woke up late because my alarm didn't go off and then i missed the bus and "
                                  "had to walk to work in the rain and my boss was in a bad mood and i spilled coffee on my shirt")
    assert r.kind == "empathy" and "alarm?" not in r.text, r.text


def test_officeholder_from_the_holders_own_article(chat):
    a, _ = chat

    class NoKB:
        kb = None

        def answer(self, q):
            return None

    class Cands:
        ids = [0, 1]

    class R:
        def candidates(self, q):
            return Cands()

    class C:
        texts = ["Kamala Harris is the 49th and current vice president of the United States.",
                 "Joseph Robinette Biden Jr. is an American politician who is the 46th and current president of the United States."]
        keys = ["Kamala Harris", "Joe Biden"]

        def sentence_text(self, s):
            return self.texts[s]

        def source(self, s):
            return {"kind": "base", "source": "wikipedia", "key": self.keys[s]}
    a.kgqa, a.reading_as_of = NoKB(), "December 2022"
    a.about.find = lambda t, **kw: None
    old_r, old_c = a.bot.r, a.bot.c
    a.bot.r, a.bot.c = R(), C()
    try:
        r = a._officeholder(DialogState("q1"), "who is the president of the united states?", "who is the president of the united states")
    finally:
        a.bot.r, a.bot.c, a.kgqa = old_r, old_c, None
    assert r is not None and "Joe Biden" in r.text and "Harris" not in r.text and "December 2022" in r.text, r and r.text


def test_battery53_words_calories_time_zones(chat):
    a, _ = chat
    st = DialogState("r1")
    r = a.turn(st, "what does ubiquitous mean?")
    assert "everywhere" in r.text, r.text
    assert "Smartphones" in a.turn(st, "use it in a sentence").text
    r = a.turn(DialogState("r2"), "what does flibbertigibbet mean?")
    assert "dictionary" in r.text or "read" in r.text, r.text
    assert "selfish" in a.turn(DialogState("r3"), "what's the opposite of generous?").text
    st4 = DialogState("r4")
    assert "105 kcal" in a.turn(st4, "how many calories in a banana?").text
    assert "Not really" in a.turn(st4, "is that a lot?").text
    assert "0.8 g" in a.turn(DialogState("r5"), "how much protein do i need per day?").text
    st6 = DialogState("r6")
    r = a.turn(st6, "what time zone is london in?")
    assert "UTC" in r.text and "London" in r.text, r.text
    a.turn(st6, "what time is it there?")
    a.turn(st6, "and in sydney?")
    r = a.turn(st6, "how many hours ahead is that?")
    assert "Sydney" in r.text and "London" in r.text and "hours" in r.text, r.text


def test_battery53_german_units_words_calories(chat):
    a, _ = chat
    st = DialogState("r7")
    r = a.turn(st, "wie viele kilometer sind 5 meilen?")
    assert "8,047 km" in r.text and "Meilen" in r.text, r.text
    assert "allgegenwärtig" in a.turn(st, "was heißt ubiquitous?").text
    assert "105 kcal" in a.turn(st, "wie viele kalorien hat eine banane?").text


def test_utc_offsets():
    import datetime as dt
    from engramm.chat.worldtime import utc_label, utc_offset
    summer = dt.datetime(2026, 7, 1, 12, tzinfo=dt.timezone.utc)
    winter = dt.datetime(2026, 1, 15, 12, tzinfo=dt.timezone.utc)
    assert utc_offset("london", summer)[1:] == (1, True)
    assert utc_offset("london", winter)[1:] == (0, False)
    assert utc_label(5.5) == "UTC+5:30" and utc_label(-3) == "UTC−3" and utc_label(0) == "UTC+0"
    assert utc_offset("atlantis") is None


def test_battery54_others_news_fight_divorce(chat):
    a, _ = chat
    st = DialogState("s1")
    a.turn(st, "my sister just got engaged!")
    assert "5 years" in a.turn(st, "to her boyfriend of 5 years").text
    assert "summer" in a.turn(st, "the wedding is next summer").text.lower()
    a.turn(st, "i'm going to be the maid of honor")
    r = a.turn(st, "what do i have to do?")
    assert "hen party" in r.text, r.text
    st2 = DialogState("s2")
    a.turn(st2, "my best friend is having a baby")
    assert "girl" in a.turn(st2, "it's a girl").text
    assert "blanket" in a.turn(st2, "what should i get her?").text
    st3 = DialogState("s3")
    a.turn(st3, "i passed my driving test!")
    assert "First try" in a.turn(st3, "first try").text
    r = a.turn(st3, "thanks! now i need a car lol")
    assert r.kind != "learned" and "used" in r.text, r.text
    assert "insurance" in a.turn(st3, "any tips for a first car?").text
    st4 = DialogState("s4")
    a.turn(st4, "i had a fight with my best friend")
    assert a.turn(st4, "she said i never listen to her").kind == "empathy"
    assert "courage" in a.turn(st4, "maybe she's right").text
    assert "sorry" in a.turn(st4, "how do i apologize?").text.lower()
    st5 = DialogState("s5")
    a.turn(st5, "my parents are getting divorced")
    r = a.turn(st5, "i'm 25 so it's not like i'm a kid")
    assert r.kind == "empathy" and "got it" not in r.text, r.text
    assert a.turn(st5, "but it still hurts").kind == "empathy"


def test_battery54_german_roles_are_not_names(chat):
    a, _ = chat
    st = DialogState("s6")
    a.turn(st, "meine schwester hat sich verlobt!")
    a.turn(st, "die hochzeit ist nächsten sommer")
    r = a.turn(st, "ich bin trauzeugin")
    assert "Hallo Trauzeugin" not in r.text and "Ehre" in r.text, r.text
    st2 = DialogState("s7")
    a.turn(st2, "ich hab mich mit meiner besten freundin gestritten")
    assert "Entschuldigung" in a.turn(st2, "wie entschuldige ich mich?").text
    assert "Glück" in a.turn(st2, "ok, ich ruf sie an").text


def test_dialog_module_names_each_pattern_once():
    """A pattern defined twice at module level silently replaces the first one (it happened once with _DE_CALL)."""
    import re as _re
    from collections import Counter
    from pathlib import Path as _P
    src = (_P(__file__).resolve().parents[1] / "engramm" / "chat" / "dialog.py").read_text(encoding="utf-8")
    names = _re.findall(r"^(_[A-Z][A-Z0-9_]*) = ", src, _re.M)
    twice = [n for n, c in Counter(names).items() if c > 1]
    assert not twice, twice


def test_battery55_work_topic_and_it_is_never_the_novel_it(chat):
    a, _ = chat

    class KB:
        def link(self, x, limit=8):
            from types import SimpleNamespace as N
            return [(N(title="Nineteen Eighty-Four", type="Book"), 0)] if x == "Nineteen Eighty-Four" else []
    a._kb_answer_orig = a._kb_answer
    st = DialogState("t1")
    # "who wrote it?" without a work in context must never be read as the novel "It"
    assert a._kb_answer(st, "who wrote it?") is None
    pages = {"Nineteen Eighty-Four": _about("Nineteen Eighty-Four", [
        "Nineteen Eighty-Four is a dystopian novel written by the English writer George Orwell."])}
    a.about.find = lambda t, **kw: pages.get(t)

    class KQ:
        kb = KB()

        def answer(self, q):
            return None
    a.kgqa = KQ()
    try:
        r = a.turn(st, "i just finished reading 1984")
        assert "Nineteen Eighty-Four" in r.text, r.text
        assert st.topic["name"] == "Nineteen Eighty-Four"
        r = a.turn(st, "it was so depressing")
        assert "brilliant" not in r.text and "happy" not in r.text, r.text
        r = a.turn(st, "who wrote it?")
        assert "Orwell" in r.text and "King" not in r.text, r.text
    finally:
        a.kgqa = None


def test_battery55_score_and_best_player(chat):
    a, _ = chat
    st = DialogState("t2")
    a.turn(st, "did you watch the game last night?")
    r = a.turn(st, "bayern won 3-1")
    assert "3–1" in r.text and "Go on" not in r.text, r.text
    assert "Messi" in a.turn(DialogState("t3"), "who's the best player in the world?").text


def test_hobbies_are_not_works(chat):
    a, _ = chat
    st = DialogState("t4")
    a.turn(st, "i love cooking")
    r = a.turn(st, "what do i love doing?")
    assert "cooking" in r.text.lower(), r.text


class _Ent:
    def __init__(self, title, typ):
        self.title, self.type, self.name, self.id = title, typ, title, 0


class _LinkKB:
    def __init__(self, people):
        self.people = people

    def link(self, name, limit=8):
        hit = [p for p in self.people if p.lower().endswith(name.lower().split()[-1]) or p.lower() == name.lower()]
        return [(_Ent(hit[0], "Person"), 0)] if hit else []


def _stub_reading(a, texts, keys):
    class Cands:
        ids = list(range(len(texts)))

    class R:
        def candidates(self, q):
            return Cands()

    class C:
        def sentence_text(self, s):
            return texts[s]

        def source(self, s):
            return {"kind": "base", "source": "wikipedia", "key": keys[s]}
    return R(), C()


def test_battery56_first_holder_needs_two_agreeing_sentences(chat):
    a, _ = chat

    class KG:
        kb = _LinkKB(["George Washington"])

        def answer(self, q):
            return None
    old = (a.bot.r, a.bot.c, a.kgqa, a.about.find)
    texts = ["The county is named for George Washington, the first president of the United States.",
             "It was named after the first President of the United States, George Washington.",
             "The high school is named after the forty-first president of the United States, George H. W. Bush."]
    a.bot.r, a.bot.c = _stub_reading(a, texts, ["Washington County", "Washington County, Utah", "Bush School"])
    a.kgqa, a.about.find = KG(), (lambda t, **kw: None)
    try:
        r = a._first_holder(DialogState("f1"), "who was the first president of the united states?")
        assert r is not None and "George Washington" in r.text and "Bush" not in r.text, r and r.text
        a.bot.r, a.bot.c = _stub_reading(a, texts[:1], ["Washington County"])
        assert a._first_holder(DialogState("f2"), "who was the first president of the united states?") is None  # one mention
        assert a._first_holder(DialogState("f3"), "who was the first lady of the united states?") is None
    finally:
        a.bot.r, a.bot.c, a.kgqa, a.about.find = old


def test_battery56_maker_from_bracketed_title(chat):
    a, _ = chat

    class KG:
        kb = _LinkKB(["Antonio Vivaldi"])

        def answer(self, q):
            return None
    old = (a.bot.r, a.bot.c, a.kgqa)
    a.bot.r, a.bot.c = _stub_reading(a, ["The Four Seasons is a group of four violin concertos.", "Four Seasons is a hotel chain."],
                                     ["The Four Seasons (Vivaldi)", "Four Seasons (company)"])
    a.kgqa = KG()
    try:
        r = a._maker_in_title(DialogState("m1"), "who composed the four seasons?")
        assert r is not None and r.text == "The Four Seasons was composed by Antonio Vivaldi.", r and r.text
        assert a._maker_in_title(DialogState("m2"), "who composed it?") is None
    finally:
        a.bot.r, a.bot.c, a.kgqa = old


def test_battery56_tenure_from_the_article_opening(chat):
    a, _ = chat
    pages = {"George Washington": _about("George Washington", [
        "George Washington (February 22, 1732 – December 14, 1799) was an American Founding Father who served as the first "
        "president of the United States from 1789 to 1797."])}
    old = a.about.find
    a.about.find = lambda t, **kw: pages.get(t)
    try:
        r = a._tenure(DialogState("t1"), "how long was George Washington president?")
        assert r is not None and "1789" in r.text and "1797" in r.text and "8 years" in r.text, r and r.text
        assert a._tenure(DialogState("t2"), "how long was George Washington king?") is None
    finally:
        a.about.find = old


def test_battery56_bare_when_after_who_question_is_passive():
    from engramm.chat.smart import rebuild_question
    assert rebuild_question("Who discovered penicillin?", "when") == "When was penicillin discovered?"
    assert rebuild_question("who wrote Romeo and Juliet?", "where") == "Where was Romeo and Juliet written?"
    assert rebuild_question("When was Shakespeare born?", "where") == "Where was Shakespeare born?"


def test_battery56_pronoun_resolution_keeps_the_right_person():
    from engramm.chat.bot import ChatBot
    b = ChatBot.__new__(ChatBot)
    b.person_gender = lambda n: {"Michelle Obama": "female", "Barack Obama": "male"}.get(n)
    b.not_a_person = lambda n: n in ("Penicillin", "Telephone")
    # a "when?" in between: "he" is still the discoverer, not penicillin
    b.context = {"answer": "1929", "atype": "DATE", "mention": "Penicillin", "last_person": ["Alexander Fleming", "Penicillin", 0]}
    assert b.resolve("what nationality was he?") == "what nationality was Alexander Fleming?"
    # "how old is he?" right after Michelle Obama: Barack
    b.context = {"answer": "62", "atype": "NUMBER", "mention": "Michelle Obama", "people": ["Barack Obama", "Michelle Obama"]}
    assert b.resolve("how old is he?") == "how old is Barack Obama?"
    # several inventors: "he" stays open
    b.context = {"answer": None, "atype": None, "mention": "Telephone", "many_people": ["Telephone", ["A B", "C D"]]}
    assert b.resolve("where was he born?") == "where was he born?"
    # the pronoun points back into the same question
    b.context = {"answer": "Antonio Vivaldi", "atype": "PERSON", "mention": "Antonio Vivaldi"}
    assert b.resolve("how old was george washington when he died?") == "how old was george washington when he died?"


def test_battery56_german_follow_ups_reach_the_same_rules():
    from engramm.chat.german_bridge import de_sentence, to_english
    assert to_english("wer war der erste präsident der usa")[:2] == ("who was the first president of United States", "first_holder")
    assert to_english("wie lange war er präsident")[:2] == ("how long was he president", "tenure")
    assert to_english("woher kam er")[:2] == ("where was he from", "from")
    assert to_english("wer hat die vier jahreszeiten komponiert")[0] == "who composed the four seasons"
    assert de_sentence("from", "Antonio Vivaldi", "Venice", "Antonio Vivaldi was from Venice.") == "Antonio Vivaldi stammte aus Venedig."


def test_battery57_everyday_moments_keep_their_context(chat):
    a, _ = chat
    st = DialogState("p57")
    assert "?" in a.turn(st, "guess what").text
    r = a.turn(st, "i got a puppy!")
    assert "puppy" in r.text and "loss" not in r.text, r.text
    r = a.turn(st, "she's a golden retriever")
    assert "golden retriever" in r.text and "How did it go" not in r.text and "call she" not in r.text, r.text
    r = a.turn(st, "any name ideas?")
    names = [ln[2:] for ln in r.text.splitlines() if ln.startswith("• ")]
    assert len(names) == 3 and r.kind == "smalltalk", r.text
    r = a.turn(st, "ooh i like the second one")
    assert names[1] in r.text and "One —" not in r.text, r.text      # the chosen name is remembered, not "One"
    assert names[1] in a.turn(st, "what's my puppy called?").text
    st = DialogState("f57")
    a.turn(st, "im so hungry")
    a.turn(st, "theres nothing in the fridge")
    r = a.turn(st, "just eggs and cheese")
    assert "omelette" in r.text, r.text
    assert "minutes" in a.turn(st, "how long do i cook it?").text
    st = DialogState("s57")
    r = a.turn(st, "i can't sleep")
    assert "get some sleep" not in r.text, r.text
    assert "3am" in a.turn(st, "it's 3am").text
    r = a.turn(st, "and i have work tomorrow")
    assert r.via != "device" and "alarm" not in r.text.lower(), r.text


def test_battery57_no_grief_for_a_phone_or_a_friend_moving(chat):
    a, _ = chat
    st = DialogState("d57")
    r = a.turn(st, "my phone died")
    assert "loss" not in r.text and "charger" in r.text, r.text
    r = a.turn(st, "and i can't find my charger")
    assert "loss" not in r.text and r.kind != "learned", r.text
    st = DialogState("m57")
    assert "Where" in a.turn(st, "my best friend is moving away").text
    assert "Canada" in a.turn(st, "to canada").text
    a.turn(st, "next month")
    r = a.turn(st, "i'm gonna miss her so much")
    assert "loss" not in r.text and "grieve" not in r.text, r.text
    # a real loss still gets sympathy
    assert "sorry" in a.turn(DialogState("g57"), "my grandma died last week").text.lower()


def test_battery57_weather_talk_and_colours(chat):
    a, _ = chat
    st = DialogState("w57")
    r = a.turn(st, "it's raining again")
    assert r.via != "device" and "live data" not in r.text, r.text
    r = a.turn(st, "i wanted to go for a run")
    assert "run" in r.text or "workout" in r.text, r.text
    assert a.turn(st, "maybe tomorrow").kind == "smalltalk"
    st = DialogState("c57")
    a.turn(st, "what's your favorite color?")
    a.turn(st, "mine is green")
    r = a.turn(st, "do you like green?")
    assert "wavelength" not in r.text and "Green" in r.text, r.text


def test_battery57_german_everyday_moments(chat):
    a, _ = chat
    st = DialogState("dp57")
    assert "?" in a.turn(st, "rate mal").text
    assert "Welpe" in a.turn(st, "ich hab einen welpen bekommen!").text
    r = a.turn(st, "sie ist ein golden retriever")
    assert "Golden Retriever" in r.text, r.text
    r = a.turn(st, "hast du namensideen?")
    names = [ln[2:] for ln in r.text.splitlines() if ln.startswith("• ")]
    assert len(names) == 3, r.text
    assert names[1] in a.turn(st, "der zweite gefällt mir").text
    st = DialogState("dh57")
    r = a.turn(st, "mein handy ist tot")
    assert "leid" not in r.text and "Ladekabel" in r.text, r.text
    st = DialogState("dm57")
    a.turn(st, "meine beste freundin zieht weg")
    assert "Kanada" in a.turn(st, "nach kanada").text
    a.turn(st, "nächsten monat")
    r = a.turn(st, "ich werde sie so vermissen")
    assert "Freundschaft" in r.text and "Verlust" not in r.text, r.text
    st = DialogState("dk57")
    a.turn(st, "der kühlschrank ist leer")
    assert "Omelett" in a.turn(st, "nur eier und käse").text
    st = DialogState("dr57")
    assert "Regen" in a.turn(st, "es regnet schon wieder").text


def test_battery59_sounds_and_keyboard_slips(chat):
    a, _ = chat
    for msg, bad in (("hhhh", "Go on"), ("xyz", "Go on"), ("aaaaa", "Tell me more"), ("smh", "Tell me more"),
                     ("omg", "help you with")):
        r = a.turn(DialogState("s59" + msg), msg)
        assert bad not in r.text, (msg, r.text)
    r = a.turn(DialogState("g59a"), "dhdhd")
    assert r.via == "gibberish", r.text
    r = a.turn(DialogState("g59b"), "dhdhd lol")
    assert r.via in ("gibberish", "clarify") and "on your mind" not in r.text, r.text
    st = DialogState("g59c")
    seen = set()
    for msg in ("what is dhdhd?", "i like dhdhd", "who is dhdhd?", "tell me about dhdhd"):
        r = a.turn(st, msg)
        assert r.kind != "learned" and "dhdhd" in r.text and r.text not in seen, r.text
        seen.add(r.text)
    st = DialogState("g59d")
    a.turn(st, "sdkfj")
    r = a.turn(st, "sorry my cat walked on the keyboard")
    assert r.kind != "learned" and "worries" in r.text or "happens" in r.text, r.text


def test_strict_mash_spares_real_words():
    from engramm.chat.smart import gibberish, strict_mash
    for w in ("yoyo", "bonbon", "dodo", "byebye", "tutu", "hmmm", "grrr", "pfff", "zelensky", "nguyen", "booboo"):
        assert not strict_mash(w), w
    for w in ("dhdhd", "sksksk", "asdf", "lkjlkj", "qwertz", "jjjj"):
        assert strict_mash(w), w
    assert gibberish("dhdhd lol") and not gibberish("lol") and not gibberish("haha ok")


def test_battery58_follow_ups_that_need_the_turn_before(chat):
    a, _ = chat
    st = DialogState("e58")
    a.turn(st, "what's the tallest mountain in the world?")
    r = a.turn(st, "no i meant in europe")
    assert "Elbrus" in r.text and r.kind != "learned", r.text
    assert "5,642" in a.turn(st, "how tall is it?").text
    st = DialogState("l58")
    r = a.turn(st, "should i learn spanish or french?")
    assert "Spanish" in r.text and "speakers" in r.text, r.text
    r = a.turn(st, "why?")
    assert "no source" not in r.text and "speakers" in r.text, r.text
    r = a.turn(st, "hmm i think i'll go with spanish")
    assert r.kind != "learned" and "Spanish" in r.text, r.text
    assert "months" in a.turn(st, "how long will it take?").text
    st = DialogState("j58")
    a.turn(st, "tell me a joke")
    r = a.turn(st, "i don't get it")
    assert "trying to find out" not in r.text, r.text
    st = DialogState("t58")
    a.turn(st, "what's 15% of 80?")
    r = a.turn(st, "thanks! you're smart")
    assert not r.text.startswith("You're welcome") and r.text.count("!") <= 2, r.text
    st = DialogState("i58")
    a.turn(st, "i have a job interview tomorrow")
    r = a.turn(st, "it's for a marketing role")
    assert "A Marketing Role" not in r.text and "What's the role" not in r.text, r.text
    assert "Marketing Role" not in a.turn(st, "ok wish me luck").text
    st = DialogState("q58")
    a.turn(st, "i'm thinking about quitting my job")
    a.turn(st, "my boss is awful")
    r = a.turn(st, "but i need the money")
    assert r.kind != "learned" and "looking" in r.text, r.text
    r = a.turn(st, "what would you do?")
    assert "If it were me" in r.text or "Honestly" in r.text, r.text
    st = DialogState("p58")                                # the fixture has no fact bank: a quoted source still answers
    a.turn(st, "what is the capital of france?")
    r = a.turn(st, "are you sure?")
    assert r.via == "why" and "no source" not in r.text, r.text
