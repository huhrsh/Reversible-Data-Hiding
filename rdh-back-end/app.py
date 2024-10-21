from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
import cv2
import numpy as np
from encode import encode, decode
from io import BytesIO
from starlette.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.mount("/images", StaticFiles(directory="images"), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RGB = np.array([0.299, 0.587, 0.114])

def predictV(value, grayij, X):
    beta = np.linalg.pinv(X.T * X) * X.T * value
    r_predict = np.linalg.det([1, grayij, grayij**2] * beta)
    if r_predict <= min(value[1, 0], value[0, 0]): r_predict = min(value[1, 0], value[0, 0])
    elif r_predict >= max(value[1, 0], value[0, 0]):
        r_predict = max(value[1, 0], value[0, 0])
    return np.round(r_predict)


def PEs(gray, img):
    pError = np.zeros(img.shape)
    predict = img.copy().astype(np.int32)
    rho = np.zeros(gray.shape)
    for i in range(2, img.shape[0] - 2):
        for j in range(2, img.shape[1] - 2):
            r = np.array([img[i + 1, j, 0], img[i, j + 1, 0], img[i + 1, j + 1, 0]]).reshape(3, 1)
            b = np.array([img[i + 1, j, 2], img[i, j + 1, 2], img[i + 1, j + 1, 2]]).reshape(3, 1)
            gr = np.array([gray[i + 1, j], gray[i, j + 1], gray[i + 1, j + 1]]).reshape(3, 1)
            X = np.asmatrix(np.column_stack(([1] * 3, gr, gr**2)))
            predict[i, j, 0] = predictV(r, gray[i, j], X)
            predict[i, j, 2] = predictV(b, gray[i, j], X)
            pError[i, j] = img[i, j] - predict[i, j]
            rho[i, j] = np.var([gray[i - 1, j], gray[i, j - 1], gray[i, j], gray[i + 1, j], gray[i, j + 1]], ddof=1)
    return predict, pError, rho


def invariant(rgb):
    return np.round(rgb[:2].dot(RGB[:2]) + 2 * (rgb[2] // 2) * RGB[2]) == np.round(rgb[:2].dot(RGB[:2]) +
                                                                                   (2 * (rgb[2] // 2) + 1) * RGB[2])


def embedMsg(img, gray, msg, mesL, selected, predict, pError, Dt):
    IMG, GRAY, pERROR = img.copy(), gray.copy(), pError.copy()
    tags = []
    La = 0
    tagsCode = '0'
    ec = 0
    location = 0
    msgIndex = 0
    for i in zip(*selected):
        if tags.count(0) < mesL:
            pERROR[i][0] = 2 * pERROR[i][0] + int(msg[msgIndex])
            pERROR[i][2] = 2 * pERROR[i][2] + ec
            ec = abs(int(IMG[i][1] - np.round((GRAY[i] - IMG[i][0] * RGB[0] - IMG[i][2] * RGB[2]) / RGB[1])))
            rgb = np.array([predict[i][loc] + pERROR[i][loc] for loc in range(3)])
            rgb[1] = np.floor((GRAY[i] - rgb[0] * RGB[0] - rgb[2] * RGB[2]) / RGB[1])
            if np.round(rgb.dot(RGB)) != GRAY[i]:
                rgb[1] = np.ceil((GRAY[i] - rgb[0] * RGB[0] - rgb[2] * RGB[2]) / RGB[1])
            if np.round(rgb.dot(RGB)) != GRAY[i]: print(f'{i}')
            D = np.linalg.norm(rgb - IMG[i])
            if np.max(rgb) > 255 or np.min(rgb) < 0 or D > Dt:
                tags.append(1)  
            else:
                tags.append(0)
                msgIndex += 1
                IMG[i] = rgb
        else:
            if La == 0:
                if np.unique(tags).size > 1:
                    tagsCode, La = ''.join([str(char) for char in tags]), len(tags)
                else:
                    La = 1
            if location == La: break
            if invariant(IMG[i]):
                IMG[i][2] = 2 * (IMG[i][2] // 2) + int(tagsCode[location])
                location += 1
    if len(tags) < mesL or location < La: return False, ec, La, len(tags), tagsCode
    print(f"=> Message: {decode(msg)}")
    return (IMG, GRAY, pERROR), ec, La, len(tags), tagsCode


def cvtGray(img):
    gray = np.zeros(img.shape[:-1])
    for i in np.argwhere(img[:, :, -1]):
        gray[i] = np.round(img[i].dot(RGB))
    return gray

# if not os.path.exists("images"):
#     os.makedirs("images")

@app.post("/embed/")
async def embed_message(file: UploadFile = File(...), message: str = Form(...)):
    try:
        print(message)
        contents = await file.read()
        npimg = np.fromstring(contents, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        gray = cvtGray(img)
        Dt = 20  # Modify as needed
        mesL = len(encode(message))

        # Proceed with the embedding process
        predict, pError, rho = PEs(gray, img)
        rhoT = 0

        while np.count_nonzero(rho < rhoT) <= mesL:
            if np.count_nonzero(rho < rhoT) == rho.size:
                raise HTTPException(status_code=400, detail="Image is too small to contain the message!")
            rhoT += 1

        enough = False
        while not enough:
            selected = [n + 2 for n in np.where(rho[2:-2, 2:-2] < rhoT)]
            if selected[0].size >= (img.shape[0] - 4)**2:
                raise HTTPException(status_code=400, detail="Image is too small to contain the message!")
            enough, lastEc, La, N, tagsCode = embedMsg(img, gray, encode(message), mesL, selected, predict, pError, Dt)
            rhoT += 0 if enough else 1

        img, gray, pError = enough
        modified_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        _, encoded_img = cv2.imencode('.png', modified_img)

        return StreamingResponse(BytesIO(encoded_img.tobytes()), media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/extract/")
async def extract_message(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        npimg = np.fromstring(contents, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        grayRcv = cvtGray(img)
        predictRcv, pErrorRcv, rhoRcv = PEs(grayRcv, img)

        border = sorted(
            list(
                set(map(tuple, np.argwhere(grayRcv == grayRcv))) -
                set(map(tuple, np.argwhere(grayRcv[1:-1, 1:-1] == grayRcv[1:-1, 1:-1]) + 1))))
        border = [str(img[loc][2] % 2) for loc in filter(lambda xy: invariant(img[xy]), border)]

        rhoT = int(''.join(border[:16]), 2)
        lastEc = int(''.join(border[16:24]), 2)
        La = int(''.join(border[24:40]), 2)
        N = int(''.join(border[40:56]), 2)

        selected = [tuple(n + 2) for n in np.argwhere(rhoRcv[2:-2, 2:-2] < rhoT)]
        tagsCode = [img[value][2] % 2 for value in filter(lambda xy: invariant(img[xy]), selected[N:])][:La]

        candidate = reversed([selected[:N][index] for index, value in enumerate(tagsCode) if value == 0])
        msgRcv = ''

        for i in candidate:
            rM = np.array([img[i[0] + 1, i[1], 0], img[i[0], i[1] + 1, 0], img[i[0] + 1, i[1] + 1, 0]]).reshape(3, 1)
            bM = np.array([img[i[0] + 1, i[1], 2], img[i[0], i[1] + 1, 2], img[i[0] + 1, i[1] + 1, 2]]).reshape(3, 1)
            grM = np.array([grayRcv[i[0] + 1, i[1]], grayRcv[i[0], i[1] + 1], grayRcv[i[0] + 1, i[1] + 1]]).reshape(3, 1)
            X = np.asmatrix(np.column_stack(([1] * 3, grM, grM**2)))
            pErrorRcv[i] = img[i] - predictRcv[i]

            msgRcv += str(int(pErrorRcv[i][0]) % 2)

        print(f"Extracted binary message: {msgRcv}")
        decoded_msg = decode(msgRcv[::-1])
        print(f"Decoded message: {decoded_msg}")
        return {"message": decoded_msg}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

