import tensorflow as tf
from tensorflow.keras.layers import Input, Conv2D, BatchNormalization, MaxPool2D, Flatten, Dense, Activation, GlobalAveragePooling2D
import matplotlib.pyplot as plt
from dataloader_eda import data_generator, display_image
from kerastuner import HyperModel
from kerastuner.tuners import RandomSearch

class MyHyperModel(HyperModel):
    def __init__(self, input_shape):
        self.input_shape = input_shape

    def build(self, hp):
        input_ = Input(shape=self.input_shape, name='image')
        x = input_
        for i in range(hp.Int('conv_blocks', 3, 5, default=3)):
            filters = hp.Int('filters_' + str(i), 32, 256, step=32)
            for _ in range(2):
                x = Conv2D(filters, kernel_size=(3, 3), padding='same')(x)
                x = BatchNormalization()(x)
                x = Activation('relu')(x)
            if i < hp.get('conv_blocks') - 1:
                x = MaxPooling2D(pool_size=(2, 2))(x)
        x = GlobalAveragePooling2D()(x)
        x = Dense(hp.Int('dense_units', 32, 128, step=32), activation='relu')(x)
        output = Dense(4, activation='linear', name='coords')(x)
        model = tf.keras.Model(inputs=input_, outputs=output)

        model.compile(optimizer=tf.keras.optimizers.Adam(hp.Choice('learning_rate', [1e-2, 1e-3, 1e-4])),
                      loss='mse',
                      metrics=['accuracy'])
        return model

def tune_model():
    hypermodel = MyHyperModel(input_shape=[380, 676, 3])

    tuner = RandomSearch(
        hypermodel,
        objective='val_accuracy',
        max_trials=10,
        executions_per_trial=2,
        directory='tuner_results',
        project_name='car_object_detection'
    )

    tuner.search_space_summary()

    # Assuming df and path are defined and valid
    tuner.search(data_generator(df=df, batch_size=32, path=path), epochs=10, validation_split=0.2)

    best_model = tuner.get_best_models(num_models=1)[0]
    best_model.save('best_model.h5')

    # Some functions to test the model. These will be called every epoch to display the current performance of the model
    def test_model(model, datagen):
        example, label = next(datagen)
        
        X = example['image']
        y = label['coords']
        
        pred_bbox = model.predict(X)[0]
        
        img = X[0]
        gt_coords = y[0]
        
        display_image(img, pred_coords=pred_bbox, norm=True)

    def test(model):
        datagen = data_generator(batch_size=1)
        
        plt.figure(figsize=(15,7))
        for i in range(3):
            plt.subplot(1, 3, i + 1)
            test_model(model, datagen)    
        plt.show()
        
    class ShowTestImages(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            test(self.model)

    return best_model
