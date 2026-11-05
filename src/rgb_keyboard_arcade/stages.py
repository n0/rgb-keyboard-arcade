"""A closed color chain: every stage's apple becomes the next snake's head."""
# Name, snake head, snake tail, Active background, Passive background.
# Each tail stays saturated and grows lighter within a narrow hue range.
PALETTES = (
    ('Ember',   (255,88,0),   (255,145,18),  (1,3,9),   (7,2,0)),
    ('Jade',    (8,126,55),   (75,245,170),  (10,6,1),  (13,8,1)),
    ('Iris',    (95,32,165),  (210,80,255), (1,11,9),  (2,13,9)),
    ('Honey',   (174,105,5),  (255,221,60),  (12,1,7),  (14,2,8)),
    ('Glacier', (20,65,165),  (70,210,255),  (7,10,1),  (9,13,2)),
    ('Guava',   (175,25,70),  (255,145,95), (9,2,14),  (11,3,16)),
    ('Lagoon',  (0,125,155),  (60,245,185),  (12,9,1),  (14,11,2)),
    ('Orchid',  (155,20,150), (250,100,245), (1,9,12),  (2,11,14)),
)

def palette(stage):
    _,head,tail,background,passive_background=PALETTES[stage%len(PALETTES)]
    apple=PALETTES[(stage+1)%len(PALETTES)][1]
    return dict(head=head,tail=tail,background=background,passive_background=passive_background,
                apple=apple,passive_apple=apple)

def name(stage):return PALETTES[stage%len(PALETTES)][0]
def normal_step(stage):return max(.16,.34-.025*stage)
