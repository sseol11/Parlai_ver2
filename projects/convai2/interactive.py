#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Basic script which allows local human keyboard input to talk to a trained model.

Examples
--------

.. code-block:: shell

  python projects/convai2/interactive.py -mf models:convai2/kvmemnn/model

When prompted, chat with the both, you will both be assigned personalities!
Use "[DONE]" to indicate you are done with that chat partner, and want a new one.
"""
import time

from parlai.core.params import ParlaiParser
from parlai.core.agents import create_agent
from parlai.core.worlds import create_task
from parlai.agents.repeat_label.repeat_label import RepeatLabelAgent
from parlai.agents.local_human.local_human import LocalHumanAgent

import random


def setup_args(parser=None):
    if parser is None:
        parser = ParlaiParser(True, True, 'Interactive chat with a model')
    parser.add_argument('-d', '--display-examples', type='bool', default=False)
    parser.add_argument(
        '--display-prettify',
        type='bool',
        default=False,
        help='Set to use a prettytable when displaying '
        'examples with text candidates',
    )
    parser.add_argument(
        '--display-ignore-fields',
        type=str,
        default='label_candidates,text_candidates',
        help='Do not display these fields',
    )
    parser.add_argument(
        '-sc',
        '--script-chateval',
        type='bool',
        default=False,
        dest='chat_script',
        help='Chateval script read file'
             'True: chateval evaluation, False: single-turn conversation with agent(original model)',
    )
    parser.add_argument(
        '-scip',
        '--chateval-input-path',
        type=str,
        default=None,
        dest='script_input_path',
        help='Chateval script input path',
    )
    parser.add_argument(
        '-scop',
        '--chateval-output-path',
        type=str,
        default=None,
        dest='script_output_path',
        help='Chateval result output path',
    )
    parser.add_argument(
        '--chateval-multi-num',
        type=int,
        default=0,
        dest='chateval_multi_num',
        help='True is chateval multiturn setting, turn coverage count.',
    )
    parser.add_argument(
        '--chateval-multi',
        type='bool',
        default=False,
        hidden=True,
        dest='chateval_multi',
        help='True is chateval multiturn setting, False just single turn.',
    )
    parser.set_defaults(model_file='models:convai2/kvmemnn/model')
    LocalHumanAgent.add_cmdline_args(parser)
    return parser

def chat_script(input_path, output_path, model_name):
    script_input_path = str(input_path)
    script_file = open(script_input_path, 'r', encoding='utf-8')

    script_out_path = str(output_path)
    timestr = time.strftime("%Y%m%d-%H%M%S")
    file_name = script_input_path.split('/')[-1].split('.')[0]

    if model_name.find(":") != -1:
        model_name = model_name.split(':')[-1]
    else:
        model_name = model_name.split('/')[-1]

    if model_name.find('blender') != -1:
        script_response = open(script_out_path + '/' + file_name + '_' + model_name.split('/')[-2] + '_' + timestr +
                               '.txt', 'w')
    else:
        script_response = open(script_out_path + '/' + file_name + '_' + model_name + '_' + timestr +
                               '.txt', 'w')

def interactive(opt, print_parser=None):
    if print_parser is not None:
        if print_parser is True and isinstance(opt, ParlaiParser):
            print_parser = opt
        elif print_parser is False:
            print_parser = None
    if isinstance(opt, ParlaiParser):
        print('[ Deprecated Warning: interactive should be passed opt not Parser ]')
        opt = opt.parse_args()
    opt['task'] = 'parlai.agents.local_human.local_human:LocalHumanAgent'
    # Create model and assign it to the specified task
    agent = create_agent(opt, requireModelExists=True)
    world = create_task(opt, agent)
    if print_parser:
        # Show arguments after loading model
        print_parser.opt = agent.opt
        print_parser.print_args()

    # Create ConvAI2 data so we can assign personas.
    convai2_opt = opt.copy()
    convai2_opt['task'] = 'convai2:both'
    convai2_agent = RepeatLabelAgent(convai2_opt)
    convai2_world = create_task(convai2_opt, convai2_agent)

    def get_new_personas():
        # Find a new episode
        while True:
            convai2_world.parley()
            msg = convai2_world.get_acts()[0]
            if msg['episode_done']:
                convai2_world.parley()
                msg = convai2_world.get_acts()[0]
                break
        txt = msg.get('text', '').split('\n')
        bot_persona = ""
        for t in txt:
            if t.startswith("partner's persona:"):
                print(t.replace("partner's ", 'your '))
            if t.startswith('your persona:'):
                bot_persona += t + '\n'
        print("Enter [DONE] if you want a new partner at any time.")
        return bot_persona

    # Now run interactive mode, chatting with personas!
    cnt = 0
    if not opt.get('chat_script'):
        while True:
            if cnt == 0:
                bot_persona = get_new_personas()
            # Run the parts of world.parley() in turn,
            # but insert persona into user message.
            acts = world.acts
            agents = world.agents
            acts[0] = agents[0].act()
            # add the persona on to the first message
            if cnt == 0:
                acts[0].force_set('text', bot_persona + acts[0].get('text', 'hi'))
            agents[1].observe(acts[0])
            acts[1] = agents[1].act()
            agents[0].observe(acts[1])
            world.update_counters()
            cnt = cnt + 1

            if opt.get('display_examples'):
                print("---")
                print(world.display())
            if world.episode_done():
                print("CHAT DONE ")
                print("In case you were curious you were talking to this bot:")
                print(bot_persona.split('\n'))
                print("\n... preparing new chat... \n")
                cnt = 0
    else:
        while True:
            input_path = opt.get('script_input_path')
            output_path = opt.get('script_output_path')
            model_name_ = opt.get('model_file')
            multi_check = opt.get('chateval_multi')
            turn_n = opt.get('chateval_multi_num')
            model_name = str(model_name_)

            script_input_path = str(input_path)
            script_file = open(script_input_path, 'r', encoding='utf-8')

            script_out_path = str(output_path)
            timestr = time.strftime("%Y%m%d-%H%M%S")
            file_name = script_input_path.split('/')[-1].split('.')[0]

            if model_name.find(":") != -1:
                model_name = model_name.split(':')[-1]
            else:
                model_name = model_name.split('/')[-1]

            if model_name.find('blender') != -1:
                script_response = open(
                    script_out_path + '/' + file_name + '_' + model_name.split('/')[-2] + '_' + timestr +
                    '.txt', 'w')
            else:
                script_response = open(script_out_path + '/' + file_name + '_' + model_name + '_' + timestr +
                                       '.txt', 'w')
            if cnt == 0:
                bot_persona = get_new_personas()
            # Run the parts of world.parley() in turn,
            # but insert persona into user message.
            acts = world.acts
            agents = world.agents
            # for raw_text in script_file:
            #     raw_text = raw_text.replace('\n', '')
            #     # acts[0] = agents[0].act()
            #     acts[0] = {'id': 'localHuman', 'episode_done': False, 'label_candidates': None, 'text': str(raw_text)}
            #     # add the persona on to the first message
            #     # if cnt == 0:
            #     #     acts[0].force_set('text', bot_persona + acts[0].get('text', 'hi'))
            #     agents[1].observe(acts[0])
            #     acts[1] = agents[1].act()
            #     agents[0].observe(acts[1])
            #
            #     result = acts[1]['text']
            #     script_response.write("%s\n" % (result))
            #
            #     world.update_counters()
            #     cnt = cnt + 1
            #
            #     if opt.get('display_examples'):
            #         print("---")
            #         print(world.display())
            #     if world.episode_done():
            #         print("CHAT DONE ")
            #         print("In case you were curious you were talking to this bot:")
            #         print(bot_persona.split('\n'))
            #         print("\n... preparing new chat... \n")
            #         cnt = 0
            # script_response.close()
            # print("script response complete!")
            # # acts[0] = {'id': 'localHuman', 'episode_done': False, 'label_candidates': None, 'text': '[DONE]'}
            # # agents[1].observe(validate(acts[0]))
            # import sys
            # sys.exit()
            count = 0
            for raw_text in script_file:
                count += 1
                # acts[0] = {'id': 'localHuman', 'episode_done': False, 'label_candidates': None, 'text': 'hi'}
                # if count > 850:
                raw_text = raw_text.replace('\n', '')
                if multi_check == True:
                    if turn_n == 2:
                        turn1 = raw_text.split('</s>')[0]
                        turn2 = raw_text.split('</s>')[1]
                        turn_temp = [turn1, turn2]

                        for index, turn_each in enumerate(turn_temp):
                            if index == 1:
                                # second turn
                                acts[0] = {'id': 'localHuman', 'episode_done': False, 'label_candidates': None,
                                           'text': str(turn_each)}
                                agents[1].observe(acts[0])
                                acts[1] = agents[1].act()
                                agents[0].observe(acts[1])

                                result = acts[1]['text']
                                script_response.write("%s\n" % (result))
                                world.update_counters()
                                cnt = cnt + 1

                            # first turn
                            acts[0] = {'id': 'localHuman', 'episode_done': True, 'label_candidates': None,
                                       'text': str(turn_each)}
                            agents[1].observe(acts[0])
                            acts[1] = agents[1].act()
                            agents[0].observe(acts[1])

                            # result = acts[1]['text']
                            # script_response.write("%s\n" % (result))
                            world.update_counters()
                            cnt = cnt + 1

                        turn_temp = []

                    elif turn_n == 3:
                        turn1 = raw_text.split('</s>')[0].replace('`', '')
                        turn2 = raw_text.split('</s>')[1].replace('`', '')
                        # turn3 = raw_text.split('</s>')[2].replace('`', '')
                        turn3 = raw_text.split('<\s>')[1].replace('`', '')
                        # if turn2.find('</s>') != -1:
                        #     turn3 = raw_text.split('</s>')[2].replace('`','')
                        # elif raw_text.find('<\s>') != -1:
                        #     turn3 = raw_text.split('<\s>')[1].replace('`','')
                        # else:
                        #     turn3 = ''
                        #     print("Check the turn utterances!!")
                        turn_temp = [turn1, turn2, turn3]

                        for index, turn_each in enumerate(turn_temp):
                            if index == 1:
                                # second turn
                                acts[0] = {'id': 'localHuman', 'episode_done': False, 'label_candidates': None,
                                           'text': str(turn_each)}
                                agents[1].observe(acts[0])
                                acts[1] = agents[1].act()
                                agents[0].observe(acts[1])

                                result = acts[1]['text']
                                # script_response.write("%s\n" % (result))
                                world.update_counters()
                                cnt = cnt + 1

                            if index == 2:
                                # third turn
                                acts[0] = {'id': 'localHuman', 'episode_done': False, 'label_candidates': None,
                                           'text': str(turn_each)}
                                agents[1].observe(acts[0])
                                acts[1] = agents[1].act()
                                agents[0].observe(acts[1])

                                result = acts[1]['text']
                                script_response.write("%s\n" % (result))
                                world.update_counters()
                                cnt = cnt + 1

                            # first turn
                            acts[0] = {'id': 'localHuman', 'episode_done': True, 'label_candidates': None,
                                       'text': str(turn_each)}
                            agents[1].observe(acts[0])
                            acts[1] = agents[1].act()
                            agents[0].observe(acts[1])

                            # result = acts[1]['text']
                            # script_response.write("%s\n" % (result))
                            world.update_counters()
                            cnt = cnt + 1

                        turn_temp = []

                else:
                    acts[0] = {'id': 'localHuman', 'episode_done': False, 'label_candidates': None,
                               'text': str(raw_text)}
                    agents[1].observe(acts[0])
                    acts[1] = agents[1].act()
                    agents[0].observe(acts[1])

                    result = acts[1]['text']
                    script_response.write("%s\n" % (result))
                    world.update_counters()
                    cnt = cnt + 1

            script_response.close()
            print("script response complete!")
            acts[0] = {'id': 'localHuman', 'episode_done': False, 'label_candidates': None, 'text': '[DONE]'}
            agents[1].observe(acts[0])
            import sys
            sys.exit()

if __name__ == '__main__':
    random.seed(42)
    parser = setup_args()
    interactive(parser.parse_args(print_args=False), print_parser=parser)
