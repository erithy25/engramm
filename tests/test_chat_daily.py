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
    assert "pineapple on pizza" in r.text and r.text.rstrip().endswith("?"), r.text
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
