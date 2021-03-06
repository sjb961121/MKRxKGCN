

import tensorflow as tf
import numpy as np
from model import MKR


def train(args, data, show_loss, show_topk):
    n_user, n_item, n_entity, n_relation = data[0], data[1], data[2], data[3]
    train_data, eval_data, test_data = data[4], data[5], data[6]
    kg=data[7]
    adj_entity, adj_relation = data[8], data[9]

    model = MKR(args, n_user, n_item, n_entity, n_relation,adj_entity,adj_relation)
    # model.load_weights('model_weights')
    # top-K evaluation settings
    user_num = 100
    k_list = [1, 2, 5, 10, 20, 50, 100]
    train_record = get_user_record(train_data, True)
    test_record = get_user_record(test_data, False)
    user_list = list(set(train_record.keys()) & set(test_record.keys()))
    if len(user_list) > user_num:
        user_list = np.random.choice(user_list, size=user_num, replace=False)
    item_set = set(list(range(n_item)))


    for step in range(args.n_epochs):
        # RS training
        np.random.shuffle(train_data)
        start = 0
        optimizers = tf.keras.optimizers.Adam(learning_rate=model.args.lr_rs)
        while start < train_data.shape[0]:
            with tf.GradientTape() as tape:
                _,loss =model.train_rs (get_feed_dict_for_rs(train_data, start, start + args.batch_size))
                g = tape.gradient(loss, model.trainable_variables)
            # optimizers = tf.keras.optimizers.Adam(learning_rate=model.args.lr_rs)
            optimizers.apply_gradients(grads_and_vars=zip(g, model.trainable_variables))
            # _,loss=model.train_rs (get_feed_dict_for_rs(train_data, start, start + args.batch_size))
            start += args.batch_size
            if show_loss:
                print(loss)

        if step % args.kge_interval == 0:
            np.random.shuffle(kg)
            start = 0
            optimizers = tf.keras.optimizers.Adam(learning_rate=model.args.lr_kge)
            while start < kg.shape[0]:
                with tf.GradientTape() as tape:
                    loss,rmse = model.train_kge(get_feed_dict_for_kge(kg, start, start + args.batch_size))
                    g = tape.gradient(loss, model.trainable_variables)
                # optimizers = tf.keras.optimizers.Adam(learning_rate=model.args.lr_kge)
                optimizers.apply_gradients(zip(g, model.trainable_variables))
                # _, rmse = model.train_kge(get_feed_dict_for_kge(kg, start, start + args.batch_size))
                start += args.batch_size
                if show_loss:
                    print(rmse)

    # CTR evaluation
    #     train_auc, train_acc = model.eval(get_feed_dict_for_rs(train_data, 0, train_data.shape[0]))
    #     eval_auc, eval_acc = model.eval(get_feed_dict_for_rs(eval_data, 0, eval_data.shape[0]))
    #     test_auc, test_acc = model.eval(get_feed_dict_for_rs(test_data, 0, test_data.shape[0]))
        train_auc, train_acc = batch_eval(model,train_data,args.batch_size)
        eval_auc, eval_acc = batch_eval(model,eval_data,args.batch_size)
        test_auc, test_acc = batch_eval(model,test_data,args.batch_size)

        print('epoch %d    train auc: %.4f  acc: %.4f    eval auc: %.4f  acc: %.4f    test auc: %.4f  acc: %.4f'
              % (step, train_auc, train_acc, eval_auc, eval_acc, test_auc, test_acc))

    model.save_weights('model_weights')

def get_feed_dict_for_rs(data, start, end):
    if data[start:end].shape[0]<end-start:
        feed_dict = [data[-(end-start):, 0],
                     data[-(end-start):, 1],
                     data[-(end-start):, 2],
                     data[-(end-start):, 1]]
    else:
        feed_dict = [data[start:end, 0],
                     data[start:end, 1],
                     data[start:end, 2],
                     data[start:end, 1]]
    return feed_dict

def get_feed_dict_for_kge(kg, start, end):
    if kg[start:end].shape[0]<end-start:
        feed_dict = [kg[-(end-start):, 0],
                     kg[-(end-start):, 0],
                     kg[-(end-start):, 1],
                     kg[-(end-start):, 2]]
    else:
        feed_dict = [kg[start:end, 0],
                 kg[start:end, 0],
                 kg[start:end, 1],
                kg[start:end, 2]]
    return feed_dict

def get_user_record(data, is_train):
    user_history_dict = dict()
    for interaction in data:
        user = interaction[0]
        item = interaction[1]
        label = interaction[2]
        if is_train or label == 1:
            if user not in user_history_dict:
                user_history_dict[user] = set()
            user_history_dict[user].add(item)
    return user_history_dict

def batch_eval(model,data, batch_size):
    start = 0
    auc_list = []
    acc_list = []
    while start + batch_size <= data.shape[0]:
        auc, acc = model.eval(get_feed_dict_for_rs(data, start, start + batch_size))
        auc_list.append(auc)
        acc_list.append(acc)
        start += batch_size
    return float(np.mean(auc_list)), float(np.mean(acc_list))