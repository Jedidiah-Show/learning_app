"""Generate the bundled datasets for the new ML pathway project kits.

The datasets are synthetic, small enough to read, and free of personal data so
they can be redistributed inside the learner repositories. They are written
with fixed values (no randomness) so the server-side report contracts, the kit
checks and the reference solutions always agree.

Run from the repository root:

    python scripts/build_ml_curriculum_data.py

Files written:

* starter_kits/machine_learning/module_4_classical_ml/data/houses.csv
* starter_kits/machine_learning/module_5_classification/data/emails.csv
* starter_kits/machine_learning/module_6_unsupervised/data/pixels.csv
* starter_kits/machine_learning/module_8_computer_vision/data/images.csv
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KITS = ROOT / 'starter_kits' / 'machine_learning'


def write_csv(path: Path, header, rows):
    """Write rows with the csv module so fields containing commas are quoted."""
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(header)
        writer.writerows(rows)
    print(f'wrote {path.relative_to(ROOT)} ({len(rows)} rows)')


def build_houses():
    """Sixteen synthetic houses for the regression part of the classical module.

    The price follows a straight line in the three features plus a small fixed
    offset, so a least-squares fit reaches a high R squared while still being
    a real regression problem to work through.
    """
    rows = [
        # size_sqm, bedrooms, location_score, price
        (48, 1, 1, 142000),
        (52, 1, 2, 168000),
        (55, 2, 1, 158000),
        (61, 2, 2, 186000),
        (64, 2, 3, 214000),
        (70, 3, 1, 196000),
        (74, 3, 2, 226000),
        (78, 3, 3, 258000),
        (85, 3, 4, 288000),
        (88, 4, 2, 286000),
        (92, 4, 3, 312000),
        (96, 4, 4, 344000),
        (102, 4, 5, 372000),
        (108, 4, 5, 396000),
        (114, 5, 4, 408000),
        (120, 5, 5, 448000),
    ]
    header = ['size_sqm', 'bedrooms', 'location_score', 'price']
    write_csv(KITS / 'module_4_classical_ml' / 'data' / 'houses.csv', header, rows)


def build_emails():
    """Thirty-six synthetic emails for the spam classifier.

    Rows E001 to E024 are the training rows and T001 to T012 are the
    evaluation rows. The evaluation set holds six spam and six not-spam
    messages, so a classifier that always predicts one class scores 0.5.
    """
    spam = [
        ('Congratulations! You are the winner of our free prize draw.',
         'Claim your free reward now, click the link and win a cash prize.'),
        ('URGENT: your account won a lottery prize, act today.',
         'Click now to claim your free lottery reward before it expires.'),
        ('Free trial ends tonight - claim your discount now.',
         'Limited time offer: order today and get a free gift with delivery.'),
        ('You have won a free gift card, confirm your details now.',
         'Click the link below to claim your prize, it is a limited time offer.'),
        ('Cheap medication online, no prescription needed.',
         'Order now and get free shipping on every repeat order.'),
        ('Make money fast working from home, no experience needed.',
         'Free training, guaranteed income, click now to start earning today.'),
        ('Exclusive crypto giveaway - double your free coins today.',
         'Limited time offer, click now and claim your free reward today.'),
        ('Your free trial of premium ends now, renew today.',
         'Click now to keep your free premium access and claim the reward.'),
        ('WINNER! Claim your free cash prize before midnight.',
         'This is your last chance, click the link and claim your free prize.'),
        ('Hot singles in your area want to meet tonight, free to join.',
         'Click now to sign up free and start chatting with new people today.'),
        ('Discounted luxury watches, free delivery and free returns.',
         'Order now, limited time offer, click here for the free shipping.'),
        ('Your package could not be delivered, pay the small fee now.',
         'Click now to reschedule delivery and avoid a late delivery charge.'),
        ('Earn passive income with our new free crypto bot.',
         'Guaranteed returns, click now and start your free trial today.'),
        ('Congratulations winner, your gift card is waiting.',
         'Claim your reward now, this free offer expires at midnight tonight.'),
        ('Best prices on designer shoes, free shipping over 50.',
         'Order today and click the link to claim your free discount today.'),
        ('URGENT: claim your free refund of 200 dollars.',
         'Click now to collect your free prize before midnight today.'),
        ('Exclusive offer just for you: 70 percent off today only.',
         'Limited time offer, order now with free delivery and a free gift.'),
        ('Your account won a prize, verify your card to claim free credit.',
         'Click now, this free reward expires today, guaranteed prize money.'),
    ]
    normal = [
        ('Standup notes and tomorrow plan', 'Attached the notes from standup and the plan for tomorrow.'),
        ('Invoice 2291 is ready', 'The invoice for March is attached, let me know if anything looks wrong.'),
        ('Project review moved to Thursday', 'We moved the project review to Thursday at ten, same room as usual.'),
        ('Lunch tomorrow?', 'Shall we get lunch tomorrow near the office at one?'),
        ('Contract for your signature', 'Please review the attached contract and send it back by Friday.'),
        ('Your order has shipped', 'Your order shipped yesterday and should arrive on Monday, tracking attached.'),
        ('Meeting notes: hiring update', 'Here are the notes from the hiring update meeting, including the two new offers.'),
        ('Re: onboarding schedule', 'Attached the onboarding schedule for the new starter, please check the dates.'),
        ('Thank you for the feedback', 'Thanks for the detailed feedback on the draft, I have updated the document.'),
        ('Expense report approved', 'Your expense report from last month was approved, the payment is scheduled.'),
        ('Reminder: quarterly targets', 'Attached the quarterly targets so we can plan the review meeting.'),
        ('Desk move on Friday', 'Your desk move to the second floor is scheduled for Friday at nine.'),
        ('Re: customer complaint', 'I spoke with the customer about the complaint and attached the summary.'),
        ('Holiday schedule', 'Attached the holiday schedule for the team, please check your dates.'),
        ('Draft budget for next quarter', 'Here is the draft budget for next quarter, please add your comments by Tuesday.'),
        ('Training session recording', 'The recording of the training session is attached, the slides are included.'),
        ('Re: supplier contract renewal', 'The supplier agreed to the renewal terms, the signed copy is attached.'),
        ('Team offsite agenda', 'Attached the agenda for the team offsite, add anything you want to cover.'),
    ]

    rows = []
    train_spam, train_normal = spam[:12], normal[:12]
    test_spam, test_normal = spam[12:], normal[12:]
    index = 0
    for label, pool in ((1, train_spam), (0, train_normal)):
        for subject, body in pool:
            index += 1
            rows.append((f'E{index:03d}', subject, body, label))
    index = 0
    for label, pool in ((1, test_spam), (0, test_normal)):
        for subject, body in pool:
            index += 1
            rows.append((f'T{index:03d}', subject, body, label))

    header = ['email_id', 'subject', 'body', 'label']
    write_csv(KITS / 'module_5_classification' / 'data' / 'emails.csv', header, rows)


def build_pixels():
    """One hundred and forty-four pixels of a 12 by 12 three-band image.

    The top band is blue, the middle band red and the bottom band green, with
    a fixed small jitter so that clustering has to do real work. Each region
    holds exactly 48 pixels.
    """
    palette = [
        (0, (28, 82, 194), (4, 6, 10)),
        (1, (201, 47, 42), (5, 7, 11)),
        (2, (44, 158, 64), (3, 8, 12)),
    ]
    rows = []
    index = 0
    for y in range(12):
        band = y // 4
        region, (r, g, b), (jr, jg, jb) = palette[band]
        for x in range(12):
            index += 1
            jitter = ((index * 7) % 9) - 4
            rows.append((
                index, x, y,
                max(0, min(255, r + ((index * 5) % 7) - 3 + jr * 0)),
                max(0, min(255, g + ((index * 3) % 7) - 3 + jg * 0)),
                max(0, min(255, b + ((index * 11) % 7) - 3 + jb * 0)),
                region,
            ))
    header = ['pixel_index', 'x', 'y', 'r', 'g', 'b', 'region']
    write_csv(KITS / 'module_6_unsupervised' / 'data' / 'pixels.csv', header, rows)


def build_images():
    """Thirty synthetic 8 by 8 greyscale images for the computer vision module.

    Class 0 images carry a bright patch in the upper half, class 1 images a
    bright patch in the lower half. Rows I001 to I020 are the training images
    and T001 to T010 are the evaluation images, five of each class.
    """
    rows = []
    counter = 0
    # Twenty training images (ten of each class), then ten evaluation images.
    for total, label in (
        (10, 0), (10, 1), (5, 0), (5, 1),
    ):
        for _ in range(total):
            counter += 1
            prefix = 'I' if counter <= 20 else 'T'
            grid = [[12 + ((counter * (row + 3) + column * 5) % 9) for column in range(8)]
                    for row in range(8)]
            centre_row = 1 if label == 0 else 5
            for row in range(centre_row, centre_row + 3):
                for column in range(2, 6):
                    grid[row][column] = 190 + ((counter * (row + 1) + column) % 25)
            pixels = [value for row in grid for value in row]
            rows.append((f'{prefix}{counter:03d}', label, *pixels))
    header = ['image_id', 'label'] + [f'p{position}' for position in range(64)]
    write_csv(KITS / 'module_8_computer_vision' / 'data' / 'images.csv', header, rows)


def main():
    build_houses()
    build_emails()
    build_pixels()
    build_images()


if __name__ == '__main__':
    main()
