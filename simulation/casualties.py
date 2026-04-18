class SimCasualty:
    def __init__(self, cid, location, audio_file, image_file, priority, output_script):
        self.id = cid
        self.location = location
        self.audio = audio_file
        self.image = image_file
        self.priority = priority
        self.output_script = output_script




def get_casualties():
    casualties = [
        SimCasualty (
                cid="A1",
                location=(38.99, -76.94),
                audio_file="../audio/normal.wav",
                image_file="../audio/normal.wav", 
                priority = 2,
                output_script = "this person has their face off"
            ),
            SimCasualty(
                cid="A2",
                location=(38.9905, -76.941),
                audio_file="../audio/testclip.wav",
                image_file="../audio/normal.wav",
                priority = 1, 
                output_script = "this person has something going on"
            ),
        ]
    return casualties

# def evaluate_all():
#     for c in casualties:
#         evaluate_casualty(c)
#     return casualties

